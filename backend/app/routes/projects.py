from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session
from uuid import uuid4
from io import StringIO
from uuid import uuid4
from datetime import datetime
import pandas as pd
import numpy as np

from app.database import SessionLocal
from app import models, schemas

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# CREATE
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


# READ ALL
@router.get("/", response_model=list[schemas.Project])
def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()


# READ ONE
@router.get("/{project_id}", response_model=schemas.Project)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# UPDATE
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


# DELETE
@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}

@router.post("/{project_id}/predict_csv")
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
            detail=f"CSV missing required columns (showing up to 10): {missing_cols[:]}"
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

    return {
        "run_id": run_id,
        "project_id": project_id,
        "rows": total,
        "summary": {
            "count_defective": count_defective,
            "avg_probability_defect": avg_probability,
            "percent_defective": percent_defective,
            "risk_buckets": {"low": low, "medium": medium, "high": high}
        },
        "results": out.to_dict(orient="records")
    }

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