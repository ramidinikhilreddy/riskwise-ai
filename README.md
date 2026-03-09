# RiskWise AI (RiseWise)

A small full‑stack demo for defect-risk prediction:
- **Backend:** FastAPI + SQLite
- **Frontend:** React (Vite)
- **Model:** scikit-learn `.joblib` + `features.json`

## Quick start (local)

### 1) Backend

```bash
cd backend
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend will be on `http://localhost:8000`.

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be on `http://localhost:5173`.

> The frontend calls the backend using `VITE_API_BASE_URL`.
> If you don’t set it, it defaults to `http://localhost:8000`.

Create `frontend/.env` (optional):

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## CSV Upload + Prediction

1. Create a project in **Projects** page.
2. Copy the **Project ID**.
3. Go to **Upload** page and upload a `.csv`.

The frontend calls:
- `POST /projects/{project_id}/predict_csv` (multipart/form-data, field name: `file`)

A compatibility alias also exists:
- `POST /projects/{project_id}/upload`

## Repo hygiene

This zip intentionally excludes local-only artifacts:
- `node_modules/`
- `.vite/`
- Python `__pycache__/`
- `.env`
- `*.db`

