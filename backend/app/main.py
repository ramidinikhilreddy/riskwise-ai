from app.routes import projects
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app import models

from pathlib import Path
import joblib, json
from typing import Any, List, Dict

ROOT_DIR = Path(__file__).resolve().parents[2]
ML_DIR = ROOT_DIR / "ml"
MODEL_PATH = ML_DIR / "rf_defect_model.joblib"
FEATURES_PATH = ML_DIR / "features.json"

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# ✅ CORS configuration added
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.model = joblib.load(MODEL_PATH)
app.state.features = json.loads(FEATURES_PATH.read_text())
app.state.threshold = 0.175

def _extract_estimator(m: Any) -> Any:
    """Unwrap common wrappers (e.g., sklearn Pipeline) to get the final estimator."""
    try:
        steps = getattr(m, "steps", None)
        if steps and isinstance(steps, list) and len(steps) > 0:
            return steps[-1][1]
    except Exception:
        pass
    return m


def _compute_global_feature_importance(model: Any, feature_names: List[str]) -> List[Dict[str, float]]:
    """Compute a simple global feature importance for many sklearn models.

    Priority:
      1) Tree models: feature_importances_
      2) Linear models: abs(coef_)
      3) Otherwise: [] (can be filled later from evaluation using permutation importance)
    """
    est = _extract_estimator(model)
    feats = list(feature_names or [])
    if not feats:
        return []

    # 1) Tree-style feature importances
    importances = getattr(est, "feature_importances_", None)
    vals: List[float] = []
    if importances is not None and len(importances) == len(feats):
        vals = [float(x) for x in importances]

    # 2) Linear-model coefficients
    if not vals:
        coef = getattr(est, "coef_", None)
        if coef is not None:
            try:
                import numpy as np
                arr = np.asarray(coef)
                if arr.ndim == 2:
                    arr = np.mean(np.abs(arr), axis=0)
                else:
                    arr = np.abs(arr)
                if arr.shape[0] == len(feats):
                    vals = [float(x) for x in arr.tolist()]
            except Exception:
                vals = []

    if not vals:
        return []

    pairs = list(zip(feats, vals))
    pairs.sort(key=lambda x: x[1], reverse=True)
    top5 = pairs[:5]
    total = sum(v for _, v in top5) or 1.0
    return [
        {"feature": f, "importance": float(v), "importance_pct": (float(v) / total) * 100.0}
        for f, v in top5
    ]


# Pre-compute global feature importance (if the model supports it)
try:
    app.state.feature_importance = _compute_global_feature_importance(app.state.model, list(app.state.features or []))
except Exception:
    app.state.feature_importance = []

# Routers
app.include_router(
    projects.router,
    prefix="/projects",
    tags=["Projects"]
)

@app.get("/")
def read_root():
    return {"message": "RiskWise Backend Running 🚀"}

@app.get("/health")
def health_check():
    return {"status": "OK"}