import logging
from pathlib import Path

log = logging.getLogger(__name__)

def prompts_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "prompts"

def load_prompt(name: str) -> str:
    p = prompts_dir() / name
    txt = p.read_text(encoding="utf-8")
    log.info("loaded prompt %s (%d chars)", name, len(txt))
    return txt