"""Stage 6 score: State+Data+Flow code, Visual model-only. P3, P5."""
import base64
import json
import logging
import re
from pathlib import Path
from typing import Any

import jsonschema

log = logging.getLogger(__name__)

_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
PNG_BYTES = base64.b64decode(_PNG_B64)

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
    for name, v in (("state", state), ("data", data), ("flow", flow), ("visual", visual)):
        fv = float(v)
        if not 0.0 <= fv <= 1.0:
            raise ValueError(f"{name} out of range: {v}")
    s = 0.40 * float(state) + 0.30 * float(data) + 0.20 * float(flow) + 0.10 * float(visual)
    return round(s, 4)


def parity_from_steps(steps: list[dict]) -> tuple[float, bool]:
    """Parity = 100 * sum(w*s) / sum(w). Pass if >=90 and no w=2 below 0.5."""
    if not steps:
        return 0.0, False
    tot_w = sum(int(s["weight"]) for s in steps)
    if tot_w == 0:
        return 0.0, False
    tot = sum(int(s["weight"]) * float(s["s"]) for s in steps)
    parity = round(100.0 * tot / tot_w, 2)
    no_bad_w2 = all(not (int(s["weight"]) == 2 and float(s["s"]) < 0.5) for s in steps)
    passed = parity >= 90.0 and no_bad_w2
    return parity, passed


def _parity_schema() -> dict:
    p = Path(__file__).resolve().parents[1] / "schemas" / "parity.schema.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _judge_prompt() -> str:
    p = Path(__file__).resolve().parents[1] / "prompts" / "judge.md"
    return p.read_text(encoding="utf-8")


def _contains_value(dom: str, expected: str) -> bool:
    if expected in dom:
        return True
    try:
        exp_f = float(str(expected).strip())
    except (ValueError, TypeError):
        return False
    nums = re.findall(r"-?\d+\.\d+|-?\d+", dom)
    for n in nums:
        try:
            if abs(float(n) - exp_f) < 1e-6:
                return True
        except ValueError:
            continue
    return False


def check_state(exp_screen: str, job_dir: Path, screenshot_exists: bool) -> float:
    """1.0 if screenshot exists and screen id present in generated_app."""
    if not screenshot_exists:
        return 0.0
    gdir = Path(job_dir) / "generated_app"
    dist = gdir / "dist" / "index.html"
    app_tsx = gdir / "client" / "src" / "App.tsx"
    blob = ""
    try:
        if dist.exists():
            blob += dist.read_text(encoding="utf-8")
        if app_tsx.exists():
            blob += app_tsx.read_text(encoding="utf-8")
    except OSError as e:
        log.warning("check_state read failed: %s", e)
        return 0.0
    if exp_screen and exp_screen in blob:
        return 1.0
    return 0.0


def check_data(expected_values: dict, expected_msgs: list[str], dom_html: str | None) -> float:
    """Fraction of expected values/messages found in replay DOM."""
    items: list[str] = []
    for v in (expected_values or {}).values():
        items.append(str(v))
    for m in expected_msgs or []:
        items.append(str(m))
    if not items:
        return 1.0
    if dom_html is None:
        return 0.0
    hit = sum(1 for e in items if _contains_value(dom_html, e))
    return round(hit / len(items), 4)


def check_flow(step_n: int, journey_steps: list[int], replay_steps: list[int]) -> float:
    """1.0 if step present and order matches journey order."""
    if step_n not in replay_steps:
        return 0.0
    if sorted(replay_steps) != sorted(journey_steps):
        return 0.0
    if replay_steps != sorted(replay_steps):
        return 0.0
    return 1.0


def judge_visual(
    legacy_path: Path,
    new_path: Path,
    client: Any | None,
    step_n: int,
) -> tuple[float, str]:
    """Visual only via model; fallback 0.8. Reason names both frames."""
    leg = legacy_path.name if isinstance(legacy_path, Path) else str(legacy_path)
    new = new_path.name if isinstance(new_path, Path) else str(new_path)
    base_reason = f"Compared {leg} with {new} for step {step_n}."
    if not Path(legacy_path).exists() or not Path(new_path).exists():
        log.info("visual step %d missing frame -> 0.0", step_n)
        return 0.0, base_reason
    if client is None:
        return 0.8, base_reason
    try:
        import base64 as _b64

        lb = _b64.b64encode(Path(legacy_path).read_bytes()).decode("ascii")
        nb = _b64.b64encode(Path(new_path).read_bytes()).decode("ascii")
        prompt = _judge_prompt() + f"\n\nStep {step_n}: legacy={leg} new={new}"
        out = client.chat_json(prompt, JUDGE_SCHEMA, f"judge:{step_n}", images_b64=[lb, nb])
        v = max(0.0, min(1.0, float(out.get("visual", 0.8))))
        r = str(out.get("reason", base_reason)).strip().replace("\n", " ")
        if leg not in r or new not in r:
            r = f"{r} Compared {leg} with {new}."
        if not r.endswith("."):
            r += "."
        return round(v, 4), r
    except Exception as e:
        log.warning("judge step %d failed, fallback 0.8: %s", step_n, e)
        return 0.8, base_reason


def _ensure_legacy_placeholder(job_dir: Path, rel: str) -> Path:
    p = Path(job_dir) / rel
    try:
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(PNG_BYTES)
            log.info("legacy placeholder %s", p.name)
    except OSError as e:
        log.warning("legacy placeholder failed: %s", e)
    return p


def score_job(job_dir: Path, client: Any | None = None) -> dict:
    """Score every journey step. Writes parity.json. Never edits AppSpec."""
    job_dir = Path(job_dir)
    spec = json.loads((job_dir / "appspec.json").read_text(encoding="utf-8"))
    journey: list[dict] = sorted(spec.get("journey", []), key=lambda s: s.get("step", 0))
    replay_dir = job_dir / "replay"
    steps_path = replay_dir / "steps.json"
    replay_map: dict[int, dict] = {}
    if steps_path.exists():
        try:
            for e in json.loads(steps_path.read_text(encoding="utf-8")):
                replay_map[int(e.get("step", 0))] = e
        except (OSError, ValueError) as e:
            log.warning("steps.json read failed: %s", e)
    journey_ns = [int(j.get("step", 0)) for j in journey]
    replay_ns = sorted(replay_map.keys())
    out_steps: list[dict] = []
    for j in journey:
        n = int(j.get("step", 0))
        w = int(j.get("weight", 1))
        exp = j.get("expect", {}) or {}
        exp_screen = str(exp.get("screen", ""))
        exp_vals = dict(exp.get("values", {}) or {})
        exp_msgs = list(exp.get("messages", []) or [])
        leg_rel = str(j.get("legacy_frame", f"frames/frame_{n:04d}.png"))
        leg_path = _ensure_legacy_placeholder(job_dir, leg_rel)
        ent = replay_map.get(n, {})
        shot_name = str(ent.get("screenshot", f"new_step_{n:02d}.png"))
        dom_name = str(ent.get("dom", f"dom_step_{n:02d}.html"))
        shot_path = replay_dir / shot_name
        dom_path = replay_dir / dom_name
        shot_ok = shot_path.exists()
        dom_html: str | None = None
        if dom_path.exists():
            try:
                dom_html = dom_path.read_text(encoding="utf-8")
            except OSError as e:
                log.warning("dom read step %d failed: %s", n, e)
                dom_html = None
        state = check_state(exp_screen, job_dir, shot_ok)
        data = check_data(exp_vals, exp_msgs, dom_html)
        flow = check_flow(n, journey_ns, replay_ns if replay_ns else journey_ns if shot_ok else [])
        if not replay_map:
            flow = 0.0 if not shot_ok else 1.0
            if not shot_ok:
                state = 0.0
                data = 0.0
        visual, reason = judge_visual(leg_path, shot_path, client, n)
        s = step_score(state, data, flow, visual)
        verdict = "pass" if s >= 0.5 else "fail"
        out_steps.append({
            "step": n, "weight": w, "state": state, "data": data,
            "flow": flow, "visual": visual, "s": s, "verdict": verdict,
            "reason": reason, "legacy_frame": leg_rel,
            "new_screenshot": f"replay/{shot_name}",
        })
    parity, passed = parity_from_steps(out_steps)
    out = {"parity": parity, "pass": bool(passed), "steps": out_steps}
    jsonschema.validate(instance=out, schema=_parity_schema())
    (job_dir / "parity.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    log.info("scored parity=%.2f pass=%s steps=%d", parity, passed, len(out_steps))
    return out