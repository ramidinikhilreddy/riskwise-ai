from app.routes import projects
from fastapi import FastAPI

from app.database import engine
from app import models

from pathlib import Path
import joblib, json

ROOT_DIR = Path(__file__).resolve().parents[2]
ML_DIR = ROOT_DIR/"ml"
MODEL_PATH = ML_DIR/"rf_defect_model.joblib"
FEATURES_PATH = ML_DIR/"features.json"

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.state.model = joblib.load(MODEL_PATH)
app.state.features = json.loads(FEATURES_PATH.read_text())
app.state.threshold = 0.175

# Routers
app.include_router(
    projects.router,
    prefix="/projects",
    tags=["Projects"]
)


@app.get("/")
def read_root():
    return {"message": "RiskWise Backend Running 🚀"}


@app.get("/health") #check
def health_check():
    return {"status": "OK"}