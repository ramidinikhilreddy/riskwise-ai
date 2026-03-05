from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey
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