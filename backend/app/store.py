"""Job dir persistence: jobs/{job_id}/..."""
import json
import logging
import shutil
import uuid
from pathlib import Path
from .config import jobs_dir

log = logging.getLogger(__name__)


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]


def job_path(job_id: str) -> Path:
    p = jobs_dir() / job_id
    p.mkdir(parents=True, exist_ok=True)
    for sub in ("frames", "replay"):
        (p / sub).mkdir(parents=True, exist_ok=True)
    return p


def list_jobs() -> list[str]:
    root = jobs_dir()
    if not root.exists():
        return []
    out = [p.name for p in root.iterdir() if p.is_dir()]
    out.sort()
    return out


def delete_job(job_id: str) -> bool:
    p = jobs_dir() / job_id
    if not p.exists():
        return False
    shutil.rmtree(p)
    log.info("deleted job %s", job_id)
    return True


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("wrote %s", path)


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))