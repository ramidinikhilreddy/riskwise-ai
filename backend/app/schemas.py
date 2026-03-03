from pydantic import BaseModel

class ProjectBase(BaseModel):
    name: str
    description: str

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: str

    class Config:
        orm_mode = True