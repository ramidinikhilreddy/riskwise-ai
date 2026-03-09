from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import uuid4
from io import StringIO
from datetime import datetime
import pandas as pd
import numpy as np

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from app.database import SessionLocal
from app import models, schemas
from app.services.github import fetch_metrics
import json
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

router = APIRouter()


def _sprint_risk_from_run(percent_defective: float, avg_probability: float) -> dict:
    """A simple, explainable sprint-risk score (0-100) derived from defect model outputs.

    This keeps the app aligned with the proposal's "sprint risk" concept without
    introducing a second ML model.
    """
    try:
        pdv = float(percent_defective)
    except Exception:
        pdv = 0.0
    try:
        ap = float(avg_probability)
    except Exception:
        ap = 0.0

    # Blend: percent defective has strong impact; avg probability provides stability.
    score = (0.65 * max(0.0, min(100.0, pdv))) + (0.35 * max(0.0, min(1.0, ap)) * 100.0)
    score = int(round(max(0.0, min(100.0, score))))

    if score < 35:
        level = "Low"
    elif score < 70:
        level = "Medium"
    else:
        level = "High"

    return {"score": score, "level": level}


def _sprint_risk_from_github(metrics: dict) -> dict:
    """Simple, explainable sprint-risk score (0-100) from GitHub activity.

    This is a heuristic (not a trained model):
    - More open issues -> higher risk
    - Higher churn -> higher risk
    - Higher velocity (closed issues + merged PRs) -> lower risk
    """
    open_issues = float(metrics.get("open_issues") or 0)
    churn = float((metrics.get("churn_additions") or 0) + (metrics.get("churn_deletions") or 0))
    velocity = float(metrics.get("velocity_14d") or 0)

    # Normalize with soft caps (tunable)
    open_n = min(open_issues / 50.0, 1.0)       # 50+ open issues => max
    churn_n = min(churn / 5000.0, 1.0)          # 5000+ line changes => max
    vel_n = min(velocity / 20.0, 1.0)           # 20+ items closed/merged in 14d => max

    # Higher open/churn increase risk; higher velocity reduces.
    score = (0.45 * open_n + 0.35 * churn_n + 0.20 * (1.0 - vel_n)) * 100.0
    score = int(round(max(0.0, min(100.0, score))))

    if score < 35:
        level = "Low"
    elif score < 70:
        level = "Medium"
    else:
        level = "High"
    return {"score": score, "level": level}


# ===============================
# DATABASE DEPENDENCY
# ===============================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===============================
# CREATE PROJECT
# ===============================
@router.post("/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(
        id=str(uuid4()),
        name=project.name,
        description=project.description
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


# ===============================
# READ ALL PROJECTS
# ===============================
@router.get("/", response_model=list[schemas.Project])
def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()


# ===============================
# READ SINGLE PROJECT
# ===============================
@router.get("/{project_id}", response_model=schemas.Project)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ===============================
# UPDATE PROJECT
# ===============================
@router.put("/{project_id}", response_model=schemas.Project)
def update_project(project_id: str, updated: schemas.ProjectCreate, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.name = updated.name
    project.description = updated.description
    db.commit()
    db.refresh(project)
    return project


# ===============================
# DELETE PROJECT
# ===============================
@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}

@router.post("/{project_id}/predict_csv")
@router.post("/{project_id}/upload")  # backward-compatible alias
async def predict_csv_for_project(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    #1) check project exists
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    #2) load model + features 
    model = request.app.state.model
    FEATURES = request.app.state.features
    threshold = request.app.state.threshold

    #3) read csv content
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")
    
    content = (await file.read()).decode("utf-8", errors="ignore")
    df = pd.read_csv(StringIO(content))

    #4) validate columns
    missing_cols = [c for c in FEATURES if c not in df.columns]
    if missing_cols:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns (showing up to 10): {missing_cols[:10]}"
        )
    
    #5) align & predict
    X = df[FEATURES].copy()
    probas = model.predict_proba(X)[:,1]
    preds = (probas >= threshold).astype(int)
    total = len(df)
    count_defective = int(preds.sum())
    avg_probability = float(probas.mean())
    percent_defective = float((count_defective/total)*100)
    
    #risk buckets using probability
    low = int((probas < 0.33).sum())
    medium = int(((probas >= 0.33) & (probas
                                       < 0.66)).sum())
    high = int((probas >= 0.66).sum())

    #6) return results (we didn't save it to DB)
    out = df.copy()
    out["probability_defect"] = probas
    out["predicted_class"] = preds
    out["risk_level"] = np.where(probas < 0.33, "Low",
                        np.where(probas < 0.66, "Medium", "High"))

    run_id = str(uuid4())

    run = models.PredictionRun(
        id=run_id,
        project_id=project_id,
        filename=file.filename,
        created_at=datetime.utcnow(),
        rows=total,
        threshold=threshold,
        avg_probability=avg_probability,
        count_defective=count_defective,
        percent_defective=percent_defective
    )

    db.add(run)
    db.commit()

    for idx, (p, c, r) in enumerate(zip(probas, preds, out["risk_level"])):
        db.add(models.PredictionRow(
            id=str(uuid4()),
            run_id=run_id,
            row_index=idx,
            probability_defect=float(p),
            predicted_class=int(c),
            risk_level=str(r)
        ))
    db.commit()

    sprint_risk = _sprint_risk_from_run(percent_defective, avg_probability)

    return {
        "run_id": run_id,
        "project_id": project_id,
        "rows": total,
        "summary": {
            "count_defective": count_defective,
            "avg_probability_defect": avg_probability,
            "percent_defective": percent_defective,
            "risk_buckets": {"low": low, "medium": medium, "high": high},
            "sprint_risk": sprint_risk,
        },
        "results": out.to_dict(orient="records")
    }


# ===============================
# DASHBOARD (LATEST RUN SUMMARY)
# ===============================
@router.get("/{project_id}/dashboard")
def get_dashboard(project_id: str, request: Request, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    run = (
        db.query(models.PredictionRun)
        .filter(models.PredictionRun.project_id == project_id)
        .order_by(models.PredictionRun.created_at.desc())
        .first()
    )
    if not run:
        # Frontend expects a 200 with empty to show "upload first" nicely
        return None

    # Bucket counts from stored rows
    buckets = dict(
        db.query(models.PredictionRow.risk_level, func.count(models.PredictionRow.id))
        .filter(models.PredictionRow.run_id == run.id)
        .group_by(models.PredictionRow.risk_level)
        .all()
    )
    low = int(buckets.get("Low", 0))
    medium = int(buckets.get("Medium", 0))
    high = int(buckets.get("High", 0))

    sprint_risk = _sprint_risk_from_run(run.percent_defective or 0.0, run.avg_probability or 0.0)

    # Top 10 highest risk rows
    top = (
        db.query(models.PredictionRow)
        .filter(models.PredictionRow.run_id == run.id)
        .order_by(models.PredictionRow.probability_defect.desc())
        .limit(10)
        .all()
    )

    feature_importance = getattr(request.app.state, "feature_importance", [])

    # Latest evaluation (optional)
    eval_row = (
        db.query(models.ModelEvaluation)
        .filter(models.ModelEvaluation.project_id == project_id)
        .order_by(models.ModelEvaluation.created_at.desc())
        .first()
    )
    latest_eval = None
    if eval_row:
        try:
            latest_eval = json.loads(eval_row.metrics_json)
            latest_eval.update({
                "evaluation_id": eval_row.id,
                "filename": eval_row.filename,
                "label_column": eval_row.label_column,
                "created_at": eval_row.created_at.isoformat() if eval_row.created_at else None,
            })
        except Exception:
            latest_eval = None

    return {
        "run_id": run.id,
        "project_id": project_id,
        "filename": run.filename,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "rows": run.rows,
        "summary": {
            "count_defective": run.count_defective,
            "avg_probability_defect": run.avg_probability,
            "percent_defective": run.percent_defective,
            "risk_buckets": {"low": low, "medium": medium, "high": high},
            "sprint_risk": sprint_risk,
        },
        "top_rows": [
            {
                "row_index": r.row_index,
                "probability_defect": r.probability_defect,
                "predicted_class": r.predicted_class,
                "risk_level": r.risk_level,
            }
            for r in top
        ],
        "feature_importance": feature_importance,
        "latest_evaluation": latest_eval,
    }


# ===============================
# MODEL EVALUATION (LABELED CSV)
# ===============================
@router.post("/{project_id}/evaluate_csv", response_model=schemas.ModelEvaluationResponse)
async def evaluate_model_for_project(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    label_column: str = Form("defect"),
    db: Session = Depends(get_db),
):
    """Evaluate model performance on a labeled CSV (must include label_column).

    Expected label values: 0/1 (or False/True). Anything truthy becomes 1.
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    model = request.app.state.model
    FEATURES = request.app.state.features
    threshold = request.app.state.threshold

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    content = (await file.read()).decode("utf-8", errors="ignore")
    df = pd.read_csv(StringIO(content))

    if label_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"CSV missing label column: '{label_column}'")

    missing_cols = [c for c in FEATURES if c not in df.columns]
    if missing_cols:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required feature columns (showing up to 10): {missing_cols[:10]}"
        )

    y_true_raw = df[label_column]
    # Coerce to 0/1
    y_true = (pd.to_numeric(y_true_raw, errors="coerce").fillna(0) != 0).astype(int).to_numpy()

    X = df[FEATURES].copy()
    probas = model.predict_proba(X)[:, 1]
    y_pred = (probas >= threshold).astype(int)

    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    cm = confusion_matrix(y_true, y_pred).tolist()

    # If the loaded model doesn't expose native importances (tree/linear),
    # compute a lightweight permutation importance using the labeled dataset.
    # This gives a model-agnostic "global" importance suitable for the dashboard.
    try:
        current_fi = getattr(request.app.state, "feature_importance", [])
        if not current_fi:
            from sklearn.inspection import permutation_importance

            # Use F1 as a sensible default for defect prediction.
            # Keep repeats low for responsiveness.
            r = permutation_importance(
                model,
                X,
                y_true,
                n_repeats=5,
                random_state=42,
                scoring="f1",
            )

            importances = [float(x) for x in r.importances_mean]
            pairs = list(zip(list(FEATURES), importances))
            pairs.sort(key=lambda x: x[1], reverse=True)
            top5 = pairs[:5]
            total = sum(v for _, v in top5) or 1.0
            request.app.state.feature_importance = [
                {"feature": f, "importance": float(v), "importance_pct": (float(v) / total) * 100.0}
                for f, v in top5
            ]
    except Exception:
        # Don't fail evaluation if permutation importance can't be computed.
        pass

    evaluation_id = str(uuid4())
    metrics = {
        "rows": int(len(df)),
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "confusion_matrix": cm,
        "threshold": float(threshold),
    }

    row = models.ModelEvaluation(
        id=evaluation_id,
        project_id=project_id,
        filename=file.filename,
        label_column=label_column,
        created_at=datetime.utcnow(),
        metrics_json=json.dumps(metrics),
    )
    db.add(row)
    db.commit()

    return {
        "project_id": project_id,
        "evaluation_id": evaluation_id,
        "filename": file.filename,
        "label_column": label_column,
        "feature_importance": getattr(request.app.state, "feature_importance", []),
        **metrics,
    }


# ===============================
# GITHUB INTEGRATION (CONNECT + METRICS)
# ===============================

@router.post("/{project_id}/github/connect", response_model=schemas.GithubRepoResponse)
def connect_github_repo(project_id: str, payload: schemas.GithubConnectRequest, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    repo_full_name = (payload.repo_full_name or "").strip()
    if "/" not in repo_full_name:
        raise HTTPException(status_code=400, detail="repo_full_name must be like 'owner/repo'")

    # Validate token + repo by making a lightweight call (optional but helpful)
    try:
        _ = fetch_metrics(repo_full_name, token=payload.token, days=1)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"GitHub validation failed: {str(e)}")

    # Upsert: keep only one connected repo per project for MVP
    existing = (
        db.query(models.GithubRepo)
        .filter(models.GithubRepo.project_id == project_id)
        .order_by(models.GithubRepo.created_at.desc())
        .first()
    )
    if existing:
        existing.repo_full_name = repo_full_name
        existing.created_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return {
            "project_id": project_id,
            "repo_full_name": existing.repo_full_name,
            "connected_at": existing.created_at.isoformat() if existing.created_at else None,
        }

    repo = models.GithubRepo(
        id=str(uuid4()),
        project_id=project_id,
        repo_full_name=repo_full_name,
        created_at=datetime.utcnow(),
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    return {
        "project_id": project_id,
        "repo_full_name": repo.repo_full_name,
        "connected_at": repo.created_at.isoformat() if repo.created_at else None,
    }


@router.get("/{project_id}/github", response_model=schemas.GithubRepoResponse)
def get_connected_repo(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    repo = (
        db.query(models.GithubRepo)
        .filter(models.GithubRepo.project_id == project_id)
        .order_by(models.GithubRepo.created_at.desc())
        .first()
    )
    if not repo:
        raise HTTPException(status_code=404, detail="No GitHub repo connected")

    return {
        "project_id": project_id,
        "repo_full_name": repo.repo_full_name,
        "connected_at": repo.created_at.isoformat() if repo.created_at else None,
    }


@router.post("/{project_id}/github/metrics", response_model=schemas.GithubMetricsResponse)
def get_github_metrics(project_id: str, payload: schemas.GithubMetricsRequest, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    repo = (
        db.query(models.GithubRepo)
        .filter(models.GithubRepo.project_id == project_id)
        .order_by(models.GithubRepo.created_at.desc())
        .first()
    )
    if not repo:
        raise HTTPException(status_code=404, detail="No GitHub repo connected")

    days = max(1, min(int(payload.days or 30), 180))

    try:
        m = fetch_metrics(repo.repo_full_name, token=payload.token, days=days)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch GitHub metrics: {str(e)}")

    metrics_dict = {
        "commits": m.commits,
        "open_issues": m.open_issues,
        "closed_issues": m.closed_issues,
        "merged_prs": m.merged_prs,
        "churn_additions": m.churn_additions,
        "churn_deletions": m.churn_deletions,
        "velocity_14d": m.velocity_14d,
    }

    sprint_risk = _sprint_risk_from_github(metrics_dict)

    # Store a snapshot for history (optional)
    snap = models.GithubMetricsSnapshot(
        id=str(uuid4()),
        project_id=project_id,
        repo_full_name=repo.repo_full_name,
        collected_at=datetime.utcnow(),
        metrics_json=json.dumps(metrics_dict),
    )
    db.add(snap)
    db.commit()

    return {
        "project_id": project_id,
        "repo_full_name": repo.repo_full_name,
        "window_days": days,
        **metrics_dict,
        "sprint_risk": sprint_risk,
    }


# ===============================
# REPORT EXPORT (HTML / PDF)
# ===============================
def _latest_run_or_404(project_id: str, db: Session) -> models.PredictionRun:
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    run = (
        db.query(models.PredictionRun)
        .filter(models.PredictionRun.project_id == project_id)
        .order_by(models.PredictionRun.created_at.desc())
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="No prediction runs yet. Upload a CSV first.")
    return run


@router.get("/{project_id}/report/html", response_class=HTMLResponse)
def export_report_html(project_id: str, request: Request, db: Session = Depends(get_db)):
    run = _latest_run_or_404(project_id, db)

    buckets = dict(
        db.query(models.PredictionRow.risk_level, func.count(models.PredictionRow.id))
        .filter(models.PredictionRow.run_id == run.id)
        .group_by(models.PredictionRow.risk_level)
        .all()
    )
    low = int(buckets.get("Low", 0))
    medium = int(buckets.get("Medium", 0))
    high = int(buckets.get("High", 0))
    sprint_risk = _sprint_risk_from_run(run.percent_defective or 0.0, run.avg_probability or 0.0)

    top = (
        db.query(models.PredictionRow)
        .filter(models.PredictionRow.run_id == run.id)
        .order_by(models.PredictionRow.probability_defect.desc())
        .limit(10)
        .all()
    )

    feature_importance = getattr(request.app.state, "feature_importance", [])
    eval_row = (
        db.query(models.ModelEvaluation)
        .filter(models.ModelEvaluation.project_id == project_id)
        .order_by(models.ModelEvaluation.created_at.desc())
        .first()
    )
    eval_metrics = None
    if eval_row:
        try:
            eval_metrics = json.loads(eval_row.metrics_json)
        except Exception:
            eval_metrics = None

    fi_html = "".join(
        [
            f"<tr><td class='mono'>{i['feature']}</td><td>{i['importance']:.6f}</td><td>{i['importance_pct']:.2f}%</td></tr>"
            for i in (feature_importance or [])
        ]
    )

    eval_html = ""
    if eval_metrics:
        cm = eval_metrics.get("confusion_matrix") or [[0, 0], [0, 0]]
        eval_html = f"""
        <div class=\"card\">
          <h2>Model evaluation (labeled dataset)</h2>
          <div class=\"kpi\"><b>Accuracy:</b> {float(eval_metrics.get('accuracy', 0.0)):.3f}</div>
          <div class=\"kpi\"><b>Precision:</b> {float(eval_metrics.get('precision', 0.0)):.3f}</div>
          <div class=\"kpi\"><b>Recall:</b> {float(eval_metrics.get('recall', 0.0)):.3f}</div>
          <div class=\"kpi\"><b>F1:</b> {float(eval_metrics.get('f1', 0.0)):.3f}</div>
          <p class=\"sub\">Dataset: <span class=\"mono\">{eval_row.filename}</span> (label column: <span class=\"mono\">{eval_row.label_column}</span>)</p>
          <h3>Confusion matrix</h3>
          <table>
            <thead><tr><th></th><th>Pred 0</th><th>Pred 1</th></tr></thead>
            <tbody>
              <tr><td><b>True 0</b></td><td>{cm[0][0]}</td><td>{cm[0][1]}</td></tr>
              <tr><td><b>True 1</b></td><td>{cm[1][0]}</td><td>{cm[1][1]}</td></tr>
            </tbody>
          </table>
        </div>
        """

    html = f"""<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\"/>
    <title>RiskWise Report</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 28px; }}
      .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 14px; margin: 12px 0; }}
      .kpi {{ display: inline-block; min-width: 240px; margin-right: 18px; }}
      table {{ border-collapse: collapse; width: 100%; }}
      th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
      th {{ background: #f5f5f5; }}
      .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
    </style>
  </head>
  <body>
    <h1>RiskWise Report</h1>
    <div class=\"card\">
      <div class=\"kpi\"><b>Project ID:</b> <span class=\"mono\">{project_id}</span></div>
      <div class=\"kpi\"><b>Run ID:</b> <span class=\"mono\">{run.id}</span></div>
      <div class=\"kpi\"><b>Uploaded CSV:</b> {run.filename or ''}</div>
      <div class=\"kpi\"><b>Created:</b> {run.created_at.isoformat() if run.created_at else ''}</div>
    </div>

    <div class=\"card\">
      <div class=\"kpi\"><b>Sprint Risk:</b> {sprint_risk['level']} ({sprint_risk['score']}/100)</div>
      <div class=\"kpi\"><b>Rows analyzed:</b> {run.rows}</div>
      <div class=\"kpi\"><b>Predicted defective:</b> {run.count_defective}</div>
      <div class=\"kpi\"><b>% defective:</b> {run.percent_defective:.2f}%</div>
      <div class=\"kpi\"><b>Avg defect probability:</b> {run.avg_probability:.3f}</div>
    </div>

    <div class=\"card\">
      <h2>Risk buckets</h2>
      <ul>
        <li>Low: {low}</li>
        <li>Medium: {medium}</li>
        <li>High: {high}</li>
      </ul>
    </div>

    <div class=\"card\">
      <h2>Top 10 highest-risk rows</h2>
      <table>
        <thead><tr><th>Row</th><th>Risk</th><th>Probability</th><th>Predicted class</th></tr></thead>
        <tbody>
          {''.join([f'<tr><td>{r.row_index}</td><td>{r.risk_level}</td><td>{r.probability_defect:.4f}</td><td>{r.predicted_class}</td></tr>' for r in top])}
        </tbody>
      </table>
    </div>

    <div class=\"card\">
      <h2>Top 5 feature importance (global)</h2>
      <table>
        <thead><tr><th>Feature</th><th>Importance</th><th>Share (top5)</th></tr></thead>
        <tbody>
          {fi_html if fi_html else '<tr><td colspan="3">Not available for this model.</td></tr>'}
        </tbody>
      </table>
    </div>

    {eval_html}
  </body>
</html>"""

    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f"attachment; filename=riskwise_report_{project_id}.html"},
    )


@router.get("/{project_id}/report/pdf")
def export_report_pdf(project_id: str, request: Request, db: Session = Depends(get_db)):
    run = _latest_run_or_404(project_id, db)

    buckets = dict(
        db.query(models.PredictionRow.risk_level, func.count(models.PredictionRow.id))
        .filter(models.PredictionRow.run_id == run.id)
        .group_by(models.PredictionRow.risk_level)
        .all()
    )
    low = int(buckets.get("Low", 0))
    medium = int(buckets.get("Medium", 0))
    high = int(buckets.get("High", 0))
    sprint_risk = _sprint_risk_from_run(run.percent_defective or 0.0, run.avg_probability or 0.0)

    top = (
        db.query(models.PredictionRow)
        .filter(models.PredictionRow.run_id == run.id)
        .order_by(models.PredictionRow.probability_defect.desc())
        .limit(10)
        .all()
    )

    feature_importance = getattr(request.app.state, "feature_importance", [])
    eval_row = (
        db.query(models.ModelEvaluation)
        .filter(models.ModelEvaluation.project_id == project_id)
        .order_by(models.ModelEvaluation.created_at.desc())
        .first()
    )
    eval_metrics = None
    if eval_row:
        try:
            eval_metrics = json.loads(eval_row.metrics_json)
        except Exception:
            eval_metrics = None

    from io import BytesIO

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    x = 0.8 * inch
    y = height - 0.9 * inch

    c.setFont("Helvetica-Bold", 18)
    c.drawString(x, y, "RiskWise Report")
    y -= 0.35 * inch

    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Project: {project_id}")
    y -= 0.18 * inch
    c.drawString(x, y, f"Run: {run.id}")
    y -= 0.18 * inch
    c.drawString(x, y, f"CSV: {run.filename or ''}")
    y -= 0.18 * inch
    c.drawString(x, y, f"Created: {run.created_at.isoformat() if run.created_at else ''}")
    y -= 0.28 * inch

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, f"Sprint Risk: {sprint_risk['level']} ({sprint_risk['score']}/100)")
    y -= 0.25 * inch

    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Rows analyzed: {run.rows}")
    y -= 0.18 * inch
    c.drawString(x, y, f"Predicted defective: {run.count_defective} ({run.percent_defective:.2f}%)")
    y -= 0.18 * inch
    c.drawString(x, y, f"Avg defect probability: {run.avg_probability:.3f}")
    y -= 0.30 * inch

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Risk buckets")
    y -= 0.22 * inch
    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Low: {low}   Medium: {medium}   High: {high}")
    y -= 0.35 * inch

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Top 10 highest-risk rows")
    y -= 0.24 * inch
    c.setFont("Helvetica", 9)
    c.drawString(x, y, "Row")
    c.drawString(x + 0.7 * inch, y, "Risk")
    c.drawString(x + 1.6 * inch, y, "Probability")
    c.drawString(x + 3.0 * inch, y, "Pred")
    y -= 0.16 * inch
    c.line(x, y, width - x, y)
    y -= 0.12 * inch

    for r in top:
        if y < 1.0 * inch:
            c.showPage()
            y = height - 0.9 * inch
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x, y, "Top 10 highest-risk rows (cont.)")
            y -= 0.3 * inch
            c.setFont("Helvetica", 9)

        c.drawString(x, y, str(r.row_index))
        c.drawString(x + 0.7 * inch, y, str(r.risk_level))
        c.drawString(x + 1.6 * inch, y, f"{r.probability_defect:.4f}")
        c.drawString(x + 3.0 * inch, y, str(r.predicted_class))
        y -= 0.16 * inch

    # Feature importance
    if y < 2.0 * inch:
        c.showPage()
        y = height - 0.9 * inch

    y -= 0.10 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Top 5 feature importance (global)")
    y -= 0.22 * inch
    c.setFont("Helvetica", 9)
    if feature_importance:
        c.drawString(x, y, "Feature")
        c.drawString(x + 2.6 * inch, y, "Importance")
        c.drawString(x + 3.6 * inch, y, "Share")
        y -= 0.14 * inch
        c.line(x, y, width - x, y)
        y -= 0.12 * inch

        for i in feature_importance:
            if y < 1.0 * inch:
                c.showPage()
                y = height - 0.9 * inch
                c.setFont("Helvetica-Bold", 12)
                c.drawString(x, y, "Top 5 feature importance (cont.)")
                y -= 0.3 * inch
                c.setFont("Helvetica", 9)
            c.drawString(x, y, str(i.get("feature")))
            c.drawString(x + 2.6 * inch, y, f"{float(i.get('importance', 0.0)):.6f}")
            c.drawString(x + 3.6 * inch, y, f"{float(i.get('importance_pct', 0.0)):.2f}%")
            y -= 0.16 * inch
    else:
        c.drawString(x, y, "Not available for this model.")
        y -= 0.18 * inch

    # Evaluation metrics
    if eval_metrics:
        if y < 2.0 * inch:
            c.showPage()
            y = height - 0.9 * inch

        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Model evaluation (labeled dataset)")
        y -= 0.22 * inch
        c.setFont("Helvetica", 10)
        c.drawString(x, y, f"Accuracy: {float(eval_metrics.get('accuracy', 0.0)):.3f}   Precision: {float(eval_metrics.get('precision', 0.0)):.3f}")
        y -= 0.18 * inch
        c.drawString(x, y, f"Recall: {float(eval_metrics.get('recall', 0.0)):.3f}   F1: {float(eval_metrics.get('f1', 0.0)):.3f}")
        y -= 0.18 * inch
        c.drawString(x, y, f"Dataset: {eval_row.filename} (label: {eval_row.label_column})")
        y -= 0.24 * inch
        cm = eval_metrics.get("confusion_matrix") or [[0, 0], [0, 0]]
        c.setFont("Helvetica", 9)
        c.drawString(x, y, "Confusion matrix (rows=true, cols=pred)")
        y -= 0.16 * inch
        c.drawString(x, y, f"True0: [{cm[0][0]}, {cm[0][1]}]   True1: [{cm[1][0]}, {cm[1][1]}]")
        y -= 0.18 * inch

    c.showPage()
    c.save()
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=riskwise_report_{project_id}.pdf"},
    )

@router.post("/{project_id}/predict_single")
def predict_single(
    project_id: str,
    req: schemas.PredictSingleRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    model = request.app.state.model
    FEATURES = request.app.state.features
    threshold = request.app.state.threshold

    # build 1-row dataframe with exact columns
    row = {feat: req.features.get(feat, None) for feat in FEATURES}
    if any(v is None for v in row.values()):
        missing = [k for k, v in row.items() if v is None]
        raise HTTPException(status_code=400, detail=f"Missing features: {missing[:10]}")

    X = pd.DataFrame([row], columns=FEATURES)

    proba = float(model.predict_proba(X)[:, 1][0])
    pred = int(proba >= threshold)
    risk = "Low" if proba < 0.33 else "Medium" if proba < 0.66 else "High"

    return {
        "project_id": project_id,
        "probability_defect": proba,
        "predicted_class": pred,
        "risk_level": risk
    }