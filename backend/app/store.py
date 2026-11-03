"""Job directory persistence with explicit creation and safe lookup."""
import json
import logging
import re
import shutil
import uuid
from pathlib import Path

from .config import jobs_dir

log = logging.getLogger(__name__)
_JOB_ID_RE = re.compile(r"^[a-f0-9]{12}$")


def validate_job_id(job_id: str) -> str:
    """Reject path separators, traversal components, and malformed identifiers."""
    if not isinstance(job_id, str) or not _JOB_ID_RE.fullmatch(job_id):
        raise ValueError("invalid job id")
    return job_id


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]


def job_path(job_id: str) -> Path:
    """Create a new job directory (or return the existing job directory)."""
    validate_job_id(job_id)
    p = jobs_dir() / job_id
    p.mkdir(parents=True, exist_ok=True)
    for sub in ("frames", "replay"):
        (p / sub).mkdir(parents=True, exist_ok=True)
    return p


def existing_job_path(job_id: str) -> Path | None:
    """Return a job directory only if it already exists; never create it."""
    validate_job_id(job_id)
    root = jobs_dir().resolve()
    p = (root / job_id).resolve()
    if p.parent != root or not p.is_dir():
        return None
    return p


def list_jobs() -> list[str]:
    root = jobs_dir()
    if not root.exists():
        return []
    out = [p.name for p in root.iterdir() if p.is_dir() and _JOB_ID_RE.fullmatch(p.name)]
    out.sort()
    return out


def delete_job(job_id: str) -> bool:
    validate_job_id(job_id)
    p = existing_job_path(job_id)
    if p is None:
        return False
    shutil.rmtree(p)
    log.info("deleted job %s", job_id)
    return True


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("wrote %s", path)


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))
