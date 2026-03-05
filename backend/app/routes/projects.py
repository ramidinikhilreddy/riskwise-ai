from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from uuid import uuid4
import pandas as pd

from app.database import SessionLocal
from app import models, schemas

router = APIRouter()


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


# ===============================
# CSV UPLOAD + STORE METRICS + RISK
# ===============================
@router.post("/{project_id}/upload")
def upload_csv(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        df = pd.read_csv(file.file)

        # ----- METRIC CALCULATION -----
        total_open = int(df["open_issues"].sum())
        total_bugs = int(df["bug_issues"].sum())
        total_closed = int(df["closed_issues"].sum())
        total_commits = int(df["commits"].sum())
        total_churn = int(df["churn_add"].sum() + df["churn_del"].sum())
        avg_velocity = float(df["velocity"].mean())

        issue_close_rate = total_closed / (total_open + total_closed)
        bug_ratio = total_bugs / (total_open + 1)

        # ----- RISK SCORING -----
        normalized_churn = min(total_churn / 20000, 1)

        risk_score = (
            (bug_ratio * 0.4) +
            (normalized_churn * 0.3) +
            ((1 - issue_close_rate) * 0.3)
        )

        if risk_score < 0.33:
            risk_level = "Low"
        elif risk_score < 0.66:
            risk_level = "Medium"
        else:
            risk_level = "High"

        # ----- SAVE TO DATABASE -----
        metrics_record = models.ProjectMetrics(
            project_id=project_id,
            total_open_issues=total_open,
            total_bug_issues=total_bugs,
            total_closed_issues=total_closed,
            total_commits=total_commits,
            total_churn=total_churn,
            average_velocity=avg_velocity,
            issue_close_rate=issue_close_rate,
            bug_ratio=bug_ratio,
            risk_score=risk_score,
            risk_level=risk_level
        )

        db.add(metrics_record)
        db.commit()

        return {
            "message": "File uploaded and risk stored successfully",
            "project_id": project_id,
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===============================
# GET STORED METRICS
# ===============================
@router.get("/{project_id}/metrics")
def get_project_metrics(project_id: str, db: Session = Depends(get_db)):

    metrics = (
        db.query(models.ProjectMetrics)
        .filter(models.ProjectMetrics.project_id == project_id)
        .order_by(models.ProjectMetrics.id.desc())
        .first()
    )

    if not metrics:
        raise HTTPException(status_code=404, detail="Metrics not found")

    return {
        "project_id": project_id,
        "metrics": {
            "total_open_issues": metrics.total_open_issues,
            "total_bug_issues": metrics.total_bug_issues,
            "total_closed_issues": metrics.total_closed_issues,
            "total_commits": metrics.total_commits,
            "total_churn": metrics.total_churn,
            "average_velocity": metrics.average_velocity,
            "issue_close_rate": metrics.issue_close_rate,
            "bug_ratio": metrics.bug_ratio
        },
        "risk_analysis": {
            "risk_score": round(metrics.risk_score, 2),
            "risk_level": metrics.risk_level
        }
    }