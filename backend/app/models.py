from pydantic import BaseModel, Field
from typing import Literal

StageId = Literal["ingest", "observe", "specify", "generate", "replay", "score"]

class Job(BaseModel):
    id: str
    status: str = "created"
    stage: str = "none"

class StageStatus(BaseModel):
    job_id: str
    stage: StageId
    state: Literal["queued", "running", "done", "error"] = "queued"
    detail: str = ""