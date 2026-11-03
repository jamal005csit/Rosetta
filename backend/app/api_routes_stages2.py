"""Stage runner API: ingest/observe/specify/generate/replay."""
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException

from backend.app.store import job_path
from backend.muse.client import MuseClient
from backend.muse.budget import CallBudget
from backend.app.config import max_calls_per_job
from backend.stages import stage1_ingest
from backend.stages.stage2_observe import observe_job
from backend.stages.stage3_specify import specify_job
from backend.stages.stage4_generate import generate_job
from backend.stages.stage5_replay import replay_job

log = logging.getLogger(__name__)
router = APIRouter()

def _client(jd: Path) -> MuseClient | None:
    try:
        return MuseClient.from_env(jd, CallBudget(max_calls_per_job()))
    except Exception as e:
        log.warning("no muse client: %s", e)
        return None

@router.post("/jobs/{job_id}/run/{stage}")
def run_stage(job_id: str, stage: str) -> dict:
    jd = job_path(job_id)
    if not jd.exists():
        raise HTTPException(404, "no job")
    c = _client(jd)
    if stage == "ingest":
        return stage1_ingest.ingest(jd)
    if stage == "observe":
        return {"n": len(observe_job(jd, client=c)["observations"])}
    if stage == "specify":
        d = specify_job(jd, client=c)
        return {"screens": len(d["screens"]), "rules": len(d["rules"])}
    if stage == "generate":
        return generate_job(jd, client=c)
    if stage == "replay":
        steps = replay_job(jd)
        return {"steps": len(steps)}
    raise HTTPException(400, "unknown stage")