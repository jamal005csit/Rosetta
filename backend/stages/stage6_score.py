"""Stage 6: score actual replay evidence using deterministic checks and model vision."""
import json
import logging
import re
from pathlib import Path
from typing import Any

import jsonschema

log = logging.getLogger(__name__)

JUDGE_SCHEMA = {
    "type": "object",
    "required": ["visual", "reason"],
    "properties": {
        "visual": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string", "minLength": 1},
    },
}


def step_score(state: float, data: float, flow: float, visual: float) -> float:
    """s = 0.40*State + 0.30*Data + 0.20*Flow + 0.10*Visual."""
    for name, value in (("state", state), ("data", data), ("flow", flow), ("visual", visual)):
        numeric = float(value)
        if not 0.0 <= numeric <= 1.0:
            raise ValueError(f"{name} out of range: {value}")
    return round(
        0.40 * float(state) + 0.30 * float(data)
        + 0.20 * float(flow) + 0.10 * float(visual),
        4,
    )


def parity_from_steps(steps: list[dict]) -> tuple[float, bool]:
    """Weighted parity; pass requires >=90 and no weight-2 step below 0.5."""
    if not steps:
        return 0.0, False
    total_weight = sum(int(step["weight"]) for step in steps)
    if total_weight <= 0:
        return 0.0, False
    weighted_score = sum(int(step["weight"]) * float(step["s"]) for step in steps)
    parity = round(100.0 * weighted_score / total_weight, 2)
    no_bad_weight_two = all(
        not (int(step["weight"]) == 2 and float(step["s"]) < 0.5)
        for step in steps
    )
    return parity, parity >= 90.0 and no_bad_weight_two


def _parity_schema() -> dict:
    path = Path(__file__).resolve().parents[1] / "schemas" / "parity.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _judge_prompt() -> str:
    path = Path(__file__).resolve().parents[1] / "prompts" / "judge.md"
    return path.read_text(encoding="utf-8")


def check_state(expected_screen: str, replay_entry: dict | None, screenshot_exists: bool) -> float:
    """Score only the active screen reported by the real browser snapshot."""
    if not replay_entry or not screenshot_exists:
        return 0.0
    return 1.0 if replay_entry.get("active_screen") == expected_screen else 0.0


def check_data(expected_values: dict, expected_messages: list[str], snapshot: dict | None) -> float:
    """Compare expected values/messages with values and text read from the live DOM."""
    expected: list[tuple[str | None, str]] = []
    for key, value in (expected_values or {}).items():
        expected.append((str(key), str(value)))
    for message in expected_messages or []:
        expected.append((None, str(message)))
    if not expected:
        return 1.0
    if not snapshot:
        return 0.0

    fields = snapshot.get("fields", {}) or {}
    page_text = str(snapshot.get("text", ""))
    hits = 0
    for key, value in expected:
        if key is not None and key in fields and str(fields[key]) == value:
            hits += 1
        elif value and value in page_text:
            hits += 1
    return round(hits / len(expected), 4)


def check_flow(expected_screen: str, replay_entry: dict | None, screenshot_exists: bool) -> float:
    """A flow succeeds only when the browser action succeeded and reached its expected screen."""
    if not replay_entry or not screenshot_exists:
        return 0.0
    if replay_entry.get("success") is not True:
        return 0.0
    return 1.0 if replay_entry.get("active_screen") == expected_screen else 0.0


def judge_visual(
    legacy_path: Path,
    new_path: Path,
    client: Any | None,
    step_number: int,
) -> tuple[float, str]:
    """Visual score requires an actual model comparison; no optimistic fallback."""
    legacy_name = legacy_path.name
    new_name = new_path.name
    reason = f"Compared {legacy_name} with {new_name} for step {step_number}."
    if not legacy_path.is_file() or not new_path.is_file():
        return 0.0, f"Visual evidence missing: {reason}"
    if client is None:
        return 0.0, f"No visual judge configured; {reason}"
    try:
        import base64
        legacy_image = base64.b64encode(legacy_path.read_bytes()).decode("ascii")
        new_image = base64.b64encode(new_path.read_bytes()).decode("ascii")
        prompt = _judge_prompt() + f"\n\nStep {step_number}: legacy={legacy_name}; new={new_name}"
        result = client.chat_json(
            prompt, JUDGE_SCHEMA, f"judge:{step_number}",
            images_b64=[legacy_image, new_image],
        )
        visual = float(result["visual"])
        explanation = str(result["reason"]).strip().replace("\n", " ")
        if not 0.0 <= visual <= 1.0 or not explanation:
            raise ValueError("visual judge returned an invalid score or empty reason")
        if legacy_name not in explanation or new_name not in explanation:
            explanation = f"{explanation} Compared {legacy_name} with {new_name}."
        return round(visual, 4), explanation
    except Exception as exc:
        log.warning("visual judge failed for step %d: %s", step_number, exc)
        return 0.0, f"Visual judge failed: {str(exc)[:300]}; {reason}"


def _safe_replay_file(replay_dir: Path, filename: str, label: str) -> Path:
    relative = Path(filename)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe {label} path in replay metadata: {filename}")
    resolved = (replay_dir / relative).resolve()
    if not resolved.is_relative_to(replay_dir.resolve()):
        raise ValueError(f"{label} path escapes replay directory: {filename}")
    return resolved


def score_job(job_dir: Path, client: Any | None = None) -> dict:
    """Score every AppSpec journey step from actual browser evidence only."""
    job_dir = Path(job_dir)
    spec = json.loads((job_dir / "appspec.json").read_text(encoding="utf-8"))
    journey = sorted(spec.get("journey", []), key=lambda row: int(row["step"]))
    replay_dir = job_dir / "replay"
    steps_path = replay_dir / "steps.json"
    if not steps_path.is_file():
        raise FileNotFoundError("replay/steps.json is missing; run genuine Playwright replay first")

    replay_rows = json.loads(steps_path.read_text(encoding="utf-8"))
    replay_map: dict[int, dict] = {}
    for row in replay_rows:
        number = int(row["step"])
        if number in replay_map:
            raise ValueError(f"duplicate replay result for step {number}")
        replay_map[number] = row

    scored_steps: list[dict] = []
    for journey_step in journey:
        number = int(journey_step["step"])
        weight = int(journey_step["weight"])
        expected = journey_step.get("expect", {}) or {}
        expected_screen = str(expected.get("screen", ""))
        expected_values = dict(expected.get("values", {}) or {})
        expected_messages = list(expected.get("messages", []) or [])
        legacy_relative = Path(journey_step["legacy_frame"])
        if legacy_relative.is_absolute() or ".." in legacy_relative.parts:
            raise ValueError(f"unsafe legacy frame path: {journey_step['legacy_frame']}")
        legacy_path = (job_dir / legacy_relative).resolve()
        if not legacy_path.is_relative_to(job_dir.resolve()) or not legacy_path.is_file():
            raise FileNotFoundError(f"legacy evidence frame is missing: {journey_step['legacy_frame']}")

        replay_entry = replay_map.get(number)
        screenshot_path = None
        snapshot = None
        if replay_entry:
            screenshot_path = _safe_replay_file(replay_dir, str(replay_entry.get("screenshot", "")), "screenshot")
            snapshot_path = _safe_replay_file(replay_dir, str(replay_entry.get("snapshot", "")), "snapshot")
        screenshot_exists = bool(screenshot_path and screenshot_path.is_file())
        if snapshot_path and snapshot_path.is_file():
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

        state = check_state(expected_screen, replay_entry, screenshot_exists)
        data = check_data(expected_values, expected_messages, snapshot)
        flow = check_flow(expected_screen, replay_entry, screenshot_exists)
        if screenshot_exists and screenshot_path is not None:
            visual, reason = judge_visual(legacy_path, screenshot_path, client, number)
        else:
            visual, reason = 0.0, "Real browser screenshot missing; visual comparison not performed."

        score = step_score(state, data, flow, visual)
        scored_steps.append({
            "step": number,
            "weight": weight,
            "state": state,
            "data": data,
            "flow": flow,
            "visual": visual,
            "s": score,
            "verdict": "pass" if score >= 0.5 else "fail",
            "reason": reason,
            "legacy_frame": str(legacy_relative).replace("\\", "/"),
            "new_screenshot": (
                "replay/" + str(replay_entry["screenshot"]).replace("\\", "/")
                if replay_entry and screenshot_exists else ""
            ),
            "action_success": bool(replay_entry and replay_entry.get("success") is True),
            "active_screen": replay_entry.get("active_screen") if replay_entry else None,
            "replay_error": replay_entry.get("error") if replay_entry else "no replay result",
        })

    parity, passed = parity_from_steps(scored_steps)
    result = {"parity": parity, "pass": bool(passed), "steps": scored_steps}
    jsonschema.validate(instance=result, schema=_parity_schema())
    (job_dir / "parity.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("scored parity=%.2f pass=%s steps=%d", parity, passed, len(scored_steps))
    return result
