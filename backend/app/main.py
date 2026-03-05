from fastapi import FastAPI
from app.routes import projects

from app.database import engine
from app import models

models.Base.metadata.create_all(bind=engine)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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