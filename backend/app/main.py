import asyncio
import json
import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from .store import (
    new_job_id,
    job_path,
    existing_job_path,
    list_jobs,
    delete_job,
)
from .models import Job
from .api_routes_stages3 import router as stages_router
from backend.export.packager import export_job

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rosetta")
app = FastAPI(title="Rosetta")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(stages_router)


def _existing_job(job_id: str) -> Path:
    try:
        jd = existing_job_path(job_id)
    except ValueError:
        raise HTTPException(400, "invalid job id")
    if jd is None:
        raise HTTPException(404, "no job")
    return jd


def stage_flags(jd: Path) -> dict:
    def has(p: Path) -> bool:
        return p.is_file()
    frames = jd / "frames"
    has_frames = frames.is_dir() and any(frames.glob("frame_*.png"))
    return {
        "ingest": bool(has_frames or has(jd / "transcript.txt")),
        "observe": has(jd / "observations.json"),
        "specify": has(jd / "appspec.json"),
        "generate": has(jd / "generated_app" / "package.json"),
        "replay": has(jd / "replay" / "steps.json"),
        "score": has(jd / "parity.json"),
        "repair": has(jd / "repair_history.json"),
        "report": has(jd / "report.html"),
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/jobs")
def create_job(f: UploadFile = File(...)) -> dict:
    if not f.filename or not f.filename.lower().endswith((".mp4", ".mov", ".mkv", ".webm")):
        raise HTTPException(400, "upload a video file")
    jid = new_job_id()
    jp = job_path(jid)
    dest = jp / "upload.mp4"
    try:
        with dest.open("wb") as output:
            while chunk := f.file.read(1024 * 1024):
                output.write(chunk)
    except Exception:
        # Do not leave a half-created job behind after a failed upload.
        delete_job(jid)
        raise
    log.info("job=%s upload=%d bytes", jid, dest.stat().st_size)
    return Job(id=jid, status="created", stage="none").model_dump()


@app.get("/jobs")
def get_jobs() -> dict:
    return {"jobs": list_jobs()}


@app.get("/jobs/{job_id}/status")
def status(job_id: str) -> dict:
    jd = _existing_job(job_id)
    files = sorted(p.name for p in jd.iterdir())
    return {"job_id": job_id, "files": files, "stages": stage_flags(jd)}


@app.delete("/jobs/{job_id}")
def remove_job(job_id: str) -> dict:
    try:
        ok = delete_job(job_id)
    except ValueError:
        raise HTTPException(400, "invalid job id")
    if not ok:
        raise HTTPException(404, "no job")
    return {"deleted": job_id}


@app.get("/jobs/{job_id}/appspec.json")
def get_appspec(job_id: str) -> FileResponse:
    p = _existing_job(job_id) / "appspec.json"
    if not p.is_file():
        raise HTTPException(404, "no appspec")
    return FileResponse(str(p), media_type="application/json")


@app.get("/jobs/{job_id}/parity.json")
def get_parity(job_id: str) -> FileResponse:
    p = _existing_job(job_id) / "parity.json"
    if not p.is_file():
        raise HTTPException(404, "no parity")
    return FileResponse(str(p), media_type="application/json")


@app.get("/jobs/{job_id}/repair_history.json")
def get_repair(job_id: str) -> FileResponse:
    p = _existing_job(job_id) / "repair_history.json"
    if not p.is_file():
        raise HTTPException(404, "no repair history")
    return FileResponse(str(p), media_type="application/json")


@app.get("/jobs/{job_id}/report.html")
def get_report(job_id: str) -> FileResponse:
    rp = _existing_job(job_id) / "report.html"
    if not rp.is_file():
        raise HTTPException(404, "no report")
    return FileResponse(str(rp), media_type="text/html")


@app.get("/jobs/{job_id}/export.zip")
def get_export(job_id: str) -> FileResponse:
    jd = _existing_job(job_id)
    try:
        z = export_job(jd)
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))
    return FileResponse(str(z), media_type="application/zip", filename="export.zip")


@app.get("/jobs/{job_id}/events")
async def events(job_id: str) -> StreamingResponse:
    jd = _existing_job(job_id)

    async def gen():
        # Keep the event stream open so clients receive stage changes rather than
        # an arbitrary five-poll snapshot. Stop when the client disconnects.
        while True:
            st = {"job_id": job_id, "stages": stage_flags(jd)}
            yield f"data: {json.dumps(st)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(gen(), media_type="text/event-stream")
