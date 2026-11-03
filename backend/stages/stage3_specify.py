"""Stage 3 specify: observations -> appspec.json + coverage ledger. P1, P2, P4."""
import json
import logging
import re
from pathlib import Path

import jsonschema

from backend.muse.client import MuseClient
from backend.stages.stage2_observe import validate_observations

log = logging.getLogger(__name__)

def appspec_schema() -> dict:
    p = Path(__file__).resolve().parents[1] / "schemas" / "appspec.schema.json"
    return json.loads(p.read_text(encoding="utf-8"))

def load_prompt(name: str) -> str:
    p = Path(__file__).resolve().parents[1] / "prompts" / name
    return p.read_text(encoding="utf-8")

def ev(t: float) -> str:
    return f"t={t:.1f}s"

def normalize_appspec(data: dict, observations: dict) -> dict:
    """Normalize confidence only; never invent evidence, frames, coverage, or fields."""
    for rule in data.get("rules", []):
        examples = rule.get("examples", [])
        try:
            confidence = float(rule.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0.0
        if len(examples) == 1:
            confidence = min(confidence, 0.6)
        rule["confidence"] = max(0.0, min(1.0, confidence))
    return data


def _evidence_times(data: dict):
    for screen in data.get("screens", []):
        yield screen.get("evidence", [])
        for field in screen.get("fields", []):
            yield field.get("evidence", [])
        for shortcut in screen.get("shortcuts", []):
            yield shortcut.get("evidence", [])
    for flow in data.get("flows", []):
        yield flow.get("evidence", [])
    for rule in data.get("rules", []):
        for example in rule.get("examples", []):
            yield example.get("evidence", [])


def validate_appspec(data: dict, observations: dict, job_dir: Path) -> None:
    jsonschema.validate(instance=data, schema=appspec_schema())
    observation_times = [float(item["t"]) for item in observations["observations"]]
    if not data.get("screens"):
        raise ValueError("AppSpec contains no observed screens")

    screen_ids = [screen["id"] for screen in data["screens"]]
    if len(screen_ids) != len(set(screen_ids)):
        raise ValueError("AppSpec screen IDs must be unique")
    screen_id_set = set(screen_ids)
    observed_frames = {item.get("frame") for item in observations["observations"] if item.get("frame")}
    if not observed_frames:
        raise ValueError("observations contain no timestamp-linked keyframe evidence")
    field_ids = {
        field["id"]
        for screen in data["screens"]
        for field in screen.get("fields", [])
    }

    for evidence_list in _evidence_times(data):
        if not evidence_list:
            raise ValueError("AppSpec item has no evidence timestamps")
        for reference in evidence_list:
            match = re.fullmatch(r"t=(\d+(?:\.\d+)?)s", reference)
            if not match or not any(abs(float(match.group(1)) - observed_time) <= 0.051 for observed_time in observation_times):
                raise ValueError(f"evidence timestamp is not present in observations: {reference!r}")

    for flow in data.get("flows", []):
        if flow["from"] not in screen_id_set or flow["to"] not in screen_id_set:
            raise ValueError(f"flow references unknown screen: {flow}")

    for journey_step in data.get("journey", []):
        if journey_step["expect"]["screen"] not in screen_id_set:
            raise ValueError(f"journey references unknown screen: {journey_step['expect']['screen']}")
        if journey_step["target"] not in field_ids:
            raise ValueError(f"journey target is not a defined observed field: {journey_step['target']}")
        frame = Path(journey_step["legacy_frame"])
        if frame.is_absolute() or ".." in frame.parts or frame.parts[0] != "frames":
            raise ValueError(f"unsafe legacy frame path: {journey_step['legacy_frame']}")
        if journey_step["legacy_frame"].replace("\\", "/") not in observed_frames:
            raise ValueError("journey frame is not attached to an observation")
        resolved = (job_dir / frame).resolve()
        if not resolved.is_relative_to(job_dir.resolve()) or not resolved.is_file():
            raise ValueError(f"legacy evidence frame does not exist: {journey_step['legacy_frame']}")

def specify_job(job_dir: Path, client: MuseClient | None = None) -> dict:
    job_dir = Path(job_dir)
    if client is None:
        raise RuntimeError(
            "AppSpec generation requires a configured Muse client. "
            "Refusing to emit a hard-coded application specification."
        )
    obs_path = job_dir / "observations.json"
    if not obs_path.is_file():
        raise FileNotFoundError("observations.json is required before AppSpec generation")
    observations = json.loads(obs_path.read_text(encoding="utf-8"))
    validate_observations(observations)
    spec_prompt = load_prompt("specifier.md")
    rule_prompt = load_prompt("rule_miner.md")
    prompt = (
        spec_prompt + "\n\nRULES:\n" + rule_prompt
        + "\n\nOBSERVATIONS:\n" + json.dumps(observations, ensure_ascii=False)[:12000]
    )
    data = client.chat_json(prompt, appspec_schema(), "specifier")
    data = normalize_appspec(data, observations)
    validate_appspec(data, observations, job_dir)
    output = job_dir / "appspec.json"
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("wrote evidence-validated %s", output)
    return data
