from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)


class PredictionRun(Base):
    __tablename__ = "prediction_runs"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), index=True)
    filename = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    rows = Column(Integer)
    threshold = Column(Float)
    avg_probability = Column(Float)
    count_defective = Column(Integer)
    percent_defective = Column(Float)
    project = relationship("Project", backref="prediction_runs")

class PredictionRow(Base):
    __tablename__ = "prediction_rows"
    id = Column(String, primary_key=True, index=True)
    run_id = Column(String, ForeignKey("prediction_runs.id"), index=True)
    row_index = Column(Integer)
    probability_defect = Column(Float)
    predicted_class = Column(Integer)
    risk_level = Column(String)
    run = relationship("PredictionRun", backref="prediction_rows")


class GithubRepo(Base):
    """A GitHub repository connected to a project.

    We intentionally do NOT store OAuth tokens / PATs in the database.
    Tokens should be provided by the client at request time.
    """

    __tablename__ = "github_repos"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), index=True)
    repo_full_name = Column(String, nullable=False)  # e.g. "owner/repo"
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", backref="github_repos")


class GithubMetricsSnapshot(Base):
    """Optional metrics snapshot for caching / history."""

    __tablename__ = "github_metrics_snapshots"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), index=True)
    repo_full_name = Column(String, nullable=False)
    collected_at = Column(DateTime, default=datetime.utcnow)
    metrics_json = Column(Text, nullable=False)

    project = relationship("Project", backref="github_metrics_snapshots")


class ModelEvaluation(Base):
    """Stores model evaluation metrics computed from a labeled dataset (CSV)."""

    __tablename__ = "model_evaluations"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), index=True)
    filename = Column(String)
    label_column = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metrics_json = Column(Text, nullable=False)

    project = relationship("Project", backref="model_evaluations")