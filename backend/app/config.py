"""Central config. Reads Meta creds only from env."""
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
except ImportError:
    log.debug("python-dotenv not installed; using process environment only")

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
        value = int(os.getenv("MAX_CALLS_PER_JOB", "50"))
        if value < 1:
            raise ValueError("MAX_CALLS_PER_JOB must be positive")
        return value
    except ValueError as exc:
        log.warning("invalid MAX_CALLS_PER_JOB (%s); using safe default 50", exc)
        return 50