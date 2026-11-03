import asyncio
import json
import logging
from pathlib import Path
from fastapi import UploadFile, File, HTTPException
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from .store import new_job_id, job_path, list_jobs, delete_job
from .models import Job
from .api_routes_stages import router as stages_router
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


def stage_flags(jd: Path) -> dict:
    def has(p: Path) -> bool:
        return p.exists()
    frames = jd / "frames"
    has_frames = frames.exists() and any(frames.glob("frame_*.png"))
    return {
        "ingest": bool(has_frames or has(jd / "transcript.txt")),
        "observe": bool(has(jd / "observations.json")),
        "specify": bool(has(jd / "appspec.json")),
        "generate": bool(has(jd / "generated_app" / "package.json")),
        "replay": bool(has(jd / "replay" / "steps.json")),
        "score": bool(has(jd / "parity.json")),
        "repair": bool(has(jd / "repair_history.json")),
        "report": bool(has(jd / "report.html")),
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
    dest.write_bytes(f.file.read())
    log.info("job=%s upload=%d bytes", jid, dest.stat().st_size)
    return Job(id=jid, status="created", stage="none").model_dump()


@app.get("/jobs")
def get_jobs() -> dict:
    return {"jobs": list_jobs()}


@app.get("/jobs/{job_id}/status")
def status(job_id: str) -> dict:
    jp = job_path(job_id)
    if not (Path(jp).parent / job_id).exists():
        raise HTTPException(404, "no job")
    jd = Path(jp).parent / job_id
    files = [p.name for p in jd.iterdir()] if jd.exists() else []
    return {"job_id": job_id, "files": files, "stages": stage_flags(jd)}


@app.delete("/jobs/{job_id}")
def remove_job(job_id: str) -> dict:
    ok = delete_job(job_id)
    if not ok:
        raise HTTPException(404, "no job")
    return {"deleted": job_id}


@app.get("/jobs/{job_id}/appspec.json")
def get_appspec(job_id: str) -> FileResponse:
    p = job_path(job_id) / "appspec.json"
    if not p.exists():
        raise HTTPException(404, "no appspec")
    return FileResponse(str(p), media_type="application/json")


@app.get("/jobs/{job_id}/parity.json")
def get_parity(job_id: str) -> FileResponse:
    p = job_path(job_id) / "parity.json"
    if not p.exists():
        raise HTTPException(404, "no parity")
    return FileResponse(str(p), media_type="application/json")


@app.get("/jobs/{job_id}/repair_history.json")
def get_repair(job_id: str) -> FileResponse:
    p = job_path(job_id) / "repair_history.json"
    if not p.exists():
        raise HTTPException(404, "no repair history")
    return FileResponse(str(p), media_type="application/json")


@app.get("/jobs/{job_id}/report.html")
def get_report(job_id: str) -> FileResponse:
    rp = job_path(job_id) / "report.html"
    if not rp.exists():
        raise HTTPException(404, "no report")
    return FileResponse(str(rp), media_type="text/html")


@app.get("/jobs/{job_id}/export.zip")
def get_export(job_id: str) -> FileResponse:
    jd = job_path(job_id)
    if not jd.exists():
        raise HTTPException(404, "no job")
    try:
        z = export_job(jd)
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))
    return FileResponse(str(z), media_type="application/zip", filename="export.zip")


@app.get("/jobs/{job_id}/events")
async def events(job_id: str) -> StreamingResponse:
    jd = job_path(job_id)
    if not jd.exists():
        raise HTTPException(404, "no job")

    async def gen():
        for _ in range(5):
            st = {"job_id": job_id, "stages": stage_flags(jd)}
            yield f"data: {json.dumps(st)}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(gen(), media_type="text/event-stream")