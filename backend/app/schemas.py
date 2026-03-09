from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class ProjectBase(BaseModel):
    name: str
    description: str

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: str

    class Config:
        orm_mode = True

class PredictSingleRequest(BaseModel):
    # Frontend sends a dictionary of feature_name -> value
    features: Dict[str, float]

class PredictionSummary(BaseModel):
    count_defective: int
    avg_probability_defect: float
    percent_defective: float
    risk_buckets: dict  # or Dict[str, int]

class PredictSingleResponse(BaseModel):
    project_id: str
    probability_defect: float
    predicted_class: int
    risk_level: str

class PredictCSVResponse(BaseModel):
    run_id: str
    project_id: str
    rows: int
    summary: PredictionSummary
    results: List[Dict[str, Any]]  # keeps it flexible for all the columns


class GithubConnectRequest(BaseModel):
    repo_full_name: str  # owner/repo
    token: Optional[str] = None  # PAT (recommended). Not stored.


class GithubRepoResponse(BaseModel):
    project_id: str
    repo_full_name: str
    connected_at: Optional[str] = None


class GithubMetricsRequest(BaseModel):
    token: Optional[str] = None  # PAT. Not stored.
    days: int = 30


class GithubMetricsResponse(BaseModel):
    project_id: str
    repo_full_name: str
    window_days: int
    commits: int
    open_issues: int
    closed_issues: int
    merged_prs: int
    churn_additions: int
    churn_deletions: int
    velocity_14d: int
    sprint_risk: Dict[str, Any]


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float
    importance_pct: float


class ModelEvaluationResponse(BaseModel):
    project_id: str
    evaluation_id: str
    filename: Optional[str] = None
    label_column: str
    rows: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    confusion_matrix: List[List[int]]