"""Stage runner API for the complete Rosetta pipeline."""
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.app.store import existing_job_path
from backend.muse.client import MuseClient
from backend.app.config import meta_key
from backend.stages import stage1_ingest
from backend.stages.stage2_observe import observe_job
from backend.stages.stage3_specify import specify_job
from backend.stages.stage4_generate import generate_job
from backend.stages.stage5_replay import replay_job
from backend.stages.stage6_score import score_job
from backend.stages.stage6_repair import repair_job
from backend.stages.stage6_report import generate_report

log = logging.getLogger(__name__)
router = APIRouter()


def _client(jd: Path) -> MuseClient | None:
    if not meta_key():
        log.warning("META_API_KEY is not configured; model-dependent stages will fail closed")
        return None
    try:
        return MuseClient.from_env(jd)
    except Exception as exc:
        log.warning("Muse client unavailable for job %s: %s", jd.name, exc)
        return None


def _job_dir(job_id: str) -> Path:
    try:
        jd = existing_job_path(job_id)
    except ValueError:
        raise HTTPException(400, "invalid job id")
    if jd is None:
        raise HTTPException(404, "no job")
    return jd


@router.post("/jobs/{job_id}/run/{stage}")
def run_stage(job_id: str, stage: str) -> dict:
    jd = _job_dir(job_id)
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
    if stage == "score":
        p = score_job(jd, client=c)
        return {"parity": p["parity"], "pass": p["pass"]}
    if stage == "repair":
        r = repair_job(jd, client=c, max_rounds=3)
        return {"rounds": r["rounds"], "final_parity": r["final_parity"], "pass": r["pass"]}
    if stage == "report":
        rp = generate_report(jd)
        return {"report": str(rp)}
    raise HTTPException(400, "unknown stage")
