"""Constrained Muse repair loop. Only existing generated_app source files may change."""
import base64
import hashlib
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from backend.stages.stage6_score import score_job
from backend.stages.stage5_replay import replay_job

log = logging.getLogger(__name__)
MAX_ROUNDS = 3
REPAIR_SCHEMA = {
    "type": "object",
    "required": ["cause", "patches"],
    "properties": {
        "cause": {"type": "string", "minLength": 1},
        "patches": {
            "type": "array", "minItems": 1, "maxItems": 3,
            "items": {
                "type": "object",
                "required": ["path", "content"],
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "content": {"type": "string", "minLength": 1}
                }
            }
        }
    }
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repair_prompt() -> str:
    prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "repair.md"
    return prompt_path.read_text(encoding="utf-8")


def _allowed_source_path(generated_dir: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"repair path is unsafe: {relative_path}")
    normalized = relative.as_posix()
    if not (normalized.startswith("client/src/") or normalized.startswith("server/")):
        raise ValueError(f"repair may only modify generated_app/client/src or generated_app/server: {relative_path}")
    if relative.suffix not in {".tsx", ".ts", ".css", ".js"}:
        raise ValueError(f"repair file type is not allowed: {relative_path}")
    target = (generated_dir / relative).resolve()
    if not target.is_relative_to(generated_dir.resolve()):
        raise ValueError(f"repair path escapes generated_app: {relative_path}")
    if not target.is_file():
        raise ValueError(f"repair may only update existing generated source files: {relative_path}")
    return target


def _source_context(generated_dir: Path) -> str:
    parts = []
    for folder in (generated_dir / "client" / "src", generated_dir / "server"):
        if not folder.is_dir():
            continue
        for source in sorted(folder.rglob("*")):
            if source.is_file() and source.suffix in {".tsx", ".ts", ".css", ".js"}:
                relative = source.relative_to(generated_dir).as_posix()
                text = source.read_text(encoding="utf-8")
                parts.append(f"\n--- FILE: {relative} ---\n{text[:12000]}")
    return "\n".join(parts)[:60000]


def _replay_evidence(job_dir: Path, step_number: int) -> tuple[dict, list[str]]:
    replay_dir = job_dir / "replay"
    rows = json.loads((replay_dir / "steps.json").read_text(encoding="utf-8"))
    entry = next((row for row in rows if int(row.get("step", -1)) == step_number), None)
    if entry is None:
        raise FileNotFoundError(f"replay evidence missing for step {step_number}")
    images = []
    for key in ("screenshot",):
        relative = Path(entry[key])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe replay evidence path: {entry[key]}")
        path = (replay_dir / relative).resolve()
        if not path.is_relative_to(replay_dir.resolve()) or not path.is_file():
            raise FileNotFoundError(f"replay image missing: {entry[key]}")
        images.append(base64.b64encode(path.read_bytes()).decode("ascii"))
    snapshot_relative = Path(entry["snapshot"])
    dom_relative = Path(entry["dom"])
    for relative in (snapshot_relative, dom_relative):
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe DOM snapshot path in replay metadata")
    snapshot_path = (replay_dir / snapshot_relative).resolve()
    dom_path = (replay_dir / dom_relative).resolve()
    if not snapshot_path.is_relative_to(replay_dir.resolve()) or not snapshot_path.is_file():
        raise FileNotFoundError("browser state snapshot is missing")
    if not dom_path.is_relative_to(replay_dir.resolve()) or not dom_path.is_file():
        raise FileNotFoundError("actual browser DOM capture is missing")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    dom_text = dom_path.read_text(encoding="utf-8")[:20000]
    return {"entry": entry, "snapshot": snapshot, "dom": dom_text}, images


def _fix_step(
    job_dir: Path,
    step_result: dict,
    journey_entry: dict,
    client: Any,
) -> tuple[str, list[str]]:
    """Ask Muse for a minimal source patch and enforce the generated_app boundary."""
    number = int(step_result["step"])
    generated_dir = job_dir / "generated_app"
    evidence, images = _replay_evidence(job_dir, number)
    legacy_relative = Path(journey_entry["legacy_frame"])
    if legacy_relative.is_absolute() or ".." in legacy_relative.parts:
        raise ValueError("unsafe legacy frame path supplied to repair")
    legacy_path = (job_dir / legacy_relative).resolve()
    if not legacy_path.is_relative_to(job_dir.resolve()) or not legacy_path.is_file():
        raise FileNotFoundError("legacy frame missing during repair")
    images.insert(0, base64.b64encode(legacy_path.read_bytes()).decode("ascii"))
    expected = journey_entry.get("expect", {}) or {}
    prompt = (
        _repair_prompt()
        + f"\n\nFAILING STEP: {number}"
        + f"\nSCORE COMPONENTS: {json.dumps({key: step_result.get(key) for key in ('state','data','flow','visual','s')})}"
        + f"\nEXPECTED: {json.dumps(expected, ensure_ascii=False)}"
        + f"\nACTUAL BROWSER EVIDENCE: {json.dumps(evidence, ensure_ascii=False)}"
        + "\n\nCURRENT GENERATED SOURCE FILES:"
        + _source_context(generated_dir)
        + "\n\nReturn complete replacement contents for the smallest set of existing source files. "
          "Paths must be relative to generated_app and must be under client/src/ or server/. "
          "Do not return diffs, change the AppSpec, change tests, alter score logic, or write dist output."
    )
    response = client.chat_json(prompt, REPAIR_SCHEMA, f"repair:{number}", images_b64=images)
    cause = str(response["cause"]).strip()
    changed_paths = []
    for patch in response["patches"]:
        target = _allowed_source_path(generated_dir, patch["path"])
        replacement = str(patch["content"])
        if len(replacement.encode("utf-8")) > 100_000:
            raise ValueError(f"repair patch too large: {patch['path']}")
        temporary = target.with_suffix(target.suffix + ".repair-tmp")
        temporary.write_text(replacement, encoding="utf-8")
        os.replace(temporary, target)
        changed_paths.append(Path(patch["path"]).as_posix())
    if not changed_paths:
        raise ValueError(f"Muse returned no applicable source changes for step {number}")
    return cause, changed_paths


def _build_generated_app(generated_dir: Path) -> None:
    command = ["cmd", "/c", "npm", "run", "build"] if os.name == "nt" else ["npm", "run", "build"]
    result = subprocess.run(
        command, cwd=str(generated_dir), capture_output=True, text=True, timeout=600
    )
    if result.returncode != 0:
        raise RuntimeError("generated React build failed after repair: " + result.stderr[-3000:])


def repair_job(job_dir: Path, client: Any | None = None, max_rounds: int = 3) -> dict:
    """Repair generated source only, rebuilding/replaying/rescoring after each round."""
    job_dir = Path(job_dir)
    appspec_path = job_dir / "appspec.json"
    original_appspec_hash = _sha256(appspec_path)
    spec = json.loads(appspec_path.read_text(encoding="utf-8"))
    journey_by_step = {int(row["step"]): row for row in spec.get("journey", [])}
    parity = score_job(job_dir, client)
    history: list[dict] = []
    rounds = max(0, min(int(max_rounds), MAX_ROUNDS))

    if not parity.get("pass") and client is None:
        raise RuntimeError("A configured Muse client is required for repair; no source will be patched heuristically.")

    completed_rounds = 0
    while completed_rounds < rounds and not parity.get("pass"):
        failing = [
            row for row in parity.get("steps", [])
            if float(row.get("state", 0)) < 1.0
            or float(row.get("data", 0)) < 1.0
            or float(row.get("flow", 0)) < 1.0
            or float(row.get("visual", 0)) < 1.0
        ]
        if not failing:
            break

        completed_rounds += 1
        round_record = {
            "round": completed_rounds,
            "parity_before": parity.get("parity"),
            "steps_reran": len(spec.get("journey", [])),
            "reran_all": True,
            "fixes": [],
        }
        for step_result in sorted(failing, key=lambda row: int(row["step"])):
            step_number = int(step_result["step"])
            cause, changed_paths = _fix_step(
                job_dir, step_result, journey_by_step[step_number], client
            )
            round_record["fixes"].append({
                "step": step_number,
                "cause": cause,
                "patch": "Updated " + ", ".join(changed_paths),
                "files": changed_paths,
                "s_before": float(step_result.get("s", 0)),
            })

        _build_generated_app(job_dir / "generated_app")
        replay_job(job_dir)
        parity = score_job(job_dir, client)
        after_scores = {int(row["step"]): float(row["s"]) for row in parity.get("steps", [])}
        for fix in round_record["fixes"]:
            fix["s_after"] = after_scores.get(int(fix["step"]), 0.0)
        round_record["parity_after"] = parity.get("parity")
        history.append(round_record)
        log.info(
            "repair round %d parity %.2f -> %.2f",
            completed_rounds, round_record["parity_before"], round_record["parity_after"]
        )

    if _sha256(appspec_path) != original_appspec_hash:
        raise AssertionError("P4 violation: AppSpec changed during repair")

    result = {
        "rounds": completed_rounds,
        "history": history,
        "final_parity": parity.get("parity"),
        "pass": parity.get("pass"),
    }
    (job_dir / "repair_history.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info(
        "repair finished rounds=%d parity=%s pass=%s",
        completed_rounds, result["final_parity"], result["pass"]
    )
    return result
