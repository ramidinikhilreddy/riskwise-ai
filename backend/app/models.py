from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)

    metrics = relationship("ProjectMetrics", back_populates="project")


class ProjectMetrics(Base):
    __tablename__ = "project_metrics"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"))

    total_open_issues = Column(Integer)
    total_bug_issues = Column(Integer)
    total_closed_issues = Column(Integer)
    total_commits = Column(Integer)
    total_churn = Column(Integer)
    average_velocity = Column(Float)
    issue_close_rate = Column(Float)
    bug_ratio = Column(Float)

    risk_score = Column(Float)
    risk_level = Column(String)

    project = relationship("Project", back_populates="metrics")