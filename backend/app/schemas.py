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