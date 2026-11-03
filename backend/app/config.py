"""Central config. Reads Meta creds only from env."""
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def jobs_dir() -> Path:
    d = Path(os.getenv("JOBS_DIR", str(repo_root() / "jobs")))
    d.mkdir(parents=True, exist_ok=True)
    return d

def meta_base() -> str:
    b = os.getenv("META_API_BASE", "https://api.meta.ai/v1").rstrip("/")
    log.debug("meta_base=%s", b)
    return b

def meta_key() -> str:
    return os.getenv("META_API_KEY", "")

def muse_model() -> str:
    return os.getenv("MUSE_MODEL", "muse-spark-1.3")

def max_calls_per_job() -> int:
    try:
        return int(os.getenv("MAX_CALLS_PER_JOB", "50"))
    except ValueError:
        return 50