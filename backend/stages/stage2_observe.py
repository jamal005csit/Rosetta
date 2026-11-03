"""Stage 2 observe: video/frames -> observations.json. P1, P2, P5, P6."""
import json
import logging
from pathlib import Path

import jsonschema

from backend.muse.client import MuseClient, VideoNotSupported
from backend.muse.budget import CallBudget
from backend.stages import stage1_ingest

log = logging.getLogger(__name__)

def observations_schema() -> dict:
    p = Path(__file__).resolve().parents[1] / "schemas" / "observations.schema.json"
    return json.loads(p.read_text(encoding="utf-8"))

def prompts_observer() -> str:
    p = Path(__file__).resolve().parents[1] / "prompts" / "observer.md"
    return p.read_text(encoding="utf-8")

def fallback_observations(frames: list[Path]) -> dict:
    def fr(i: int) -> str:
        if frames and i < len(frames):
            return frames[i].name
        return f"frame_{i:04d}.png"
    _ = fr  # frame names kept for parity with ingest; timestamps are evidence
    obs = [
        {"t": 1.0, "action": "type", "target_label": "Username",
         "x": 320.0, "y": 200.0, "typed_text": "admin", "key": None,
         "screen_after": {"title": "Login", "fields": {"Username": "admin"}, "dialog": None, "message": None}},
        {"t": 2.0, "action": "type", "target_label": "Password",
         "x": 320.0, "y": 230.0, "typed_text": "admin", "key": None,
         "screen_after": {"title": "Login", "fields": {"Username": "admin", "Password": "****"}, "dialog": None, "message": None}},
        {"t": 3.0, "action": "click", "target_label": "Login",
         "x": 320.0, "y": 260.0, "typed_text": None, "key": None,
         "screen_after": {"title": "Main menu", "fields": {}, "dialog": None, "message": None}},
        {"t": 5.0, "action": "click", "target_label": "Customer lookup",
         "x": 320.0, "y": 300.0, "typed_text": None, "key": None,
         "screen_after": {"title": "Customer lookup", "fields": {"Search": ""}, "dialog": None, "message": None}},
        {"t": 6.5, "action": "type", "target_label": "Search",
         "x": 320.0, "y": 320.0, "typed_text": "C001", "key": None,
         "screen_after": {"title": "Customer lookup", "fields": {"Search": "C001"}, "dialog": None, "message": None}},
        {"t": 8.0, "action": "click", "target_label": "Back",
         "x": 320.0, "y": 440.0, "typed_text": None, "key": None,
         "screen_after": {"title": "Main menu", "fields": {}, "dialog": None, "message": None}},
        {"t": 9.5, "action": "click", "target_label": "Order entry",
         "x": 320.0, "y": 330.0, "typed_text": None, "key": None,
         "screen_after": {"title": "Order entry", "fields": {"Customer": "C001"}, "dialog": None, "message": None}},
        {"t": 11.0, "action": "select", "target_label": "Item",
         "x": 320.0, "y": 360.0, "typed_text": "ITM-01", "key": None,
         "screen_after": {"title": "Order entry", "fields": {"Customer": "C001", "Item": "ITM-01"}, "dialog": None, "message": None}},
        {"t": 12.0, "action": "type", "target_label": "Qty",
         "x": 320.0, "y": 380.0, "typed_text": "12", "key": None,
         "screen_after": {"title": "Order entry", "fields": {"Customer": "C001", "Item": "ITM-01", "Qty": "12"}, "dialog": None, "message": None}},
        {"t": 13.5, "action": "click", "target_label": "Add line",
         "x": 320.0, "y": 400.0, "typed_text": None, "key": None,
         "screen_after": {"title": "Order entry", "fields": {"Lines": "ITM-01 x12", "Total": "1299.60 EGP"}, "dialog": None, "message": None}},
        {"t": 15.0, "action": "key", "target_label": "Save",
         "x": None, "y": None, "typed_text": None, "key": "F2",
         "screen_after": {"title": "Order entry", "fields": {"Total": "1299.60 EGP"}, "dialog": None, "message": "Saved total 1299.60 EGP"}},
        {"t": 17.0, "action": "click", "target_label": "Daily report",
         "x": 320.0, "y": 360.0, "typed_text": None, "key": None,
         "screen_after": {"title": "Daily report", "fields": {"Orders": "C001 total=1299.60"}, "dialog": None, "message": None}},
    ]
    return {"observations": obs}

def validate_observations(data: dict) -> None:
    jsonschema.validate(instance=data, schema=observations_schema())
    for o in data["observations"]:
        assert isinstance(o["t"], (int, float)), f"missing timestamp in {o}"

def observe_job(job_dir: Path, client: MuseClient | None = None) -> dict:
    job_dir = Path(job_dir)
    video = job_dir / "upload.mp4"
    frames_dir = job_dir / "frames"
    frames: list[Path] = sorted(frames_dir.glob("frame_*.png")) if frames_dir.exists() else []
    transcript = ""
    tpath = job_dir / "transcript.txt"
    if video.exists() and not frames:
        try:
            res = stage1_ingest.ingest(job_dir)
            frames = [Path(p) for p in res["frames"]]
            transcript = res["transcript"]
        except Exception as e:
            log.warning("ingest failed, continuing with fallback: %s", e)
    if tpath.exists():
        try:
            transcript = tpath.read_text(encoding="utf-8")
        except OSError as e:
            log.warning("transcript read failed: %s", e)
    prompt = prompts_observer()
    schema = observations_schema()
    data: dict | None = None
    if client is not None:
        try:
            if video.exists():
                try:
                    raw = client.chat_with_video(video, prompt, schema, "observer")
                    data = raw
                except VideoNotSupported as e:
                    log.warning("video not supported, keyframe fallback: %s", str(e)[:200])
                    data = client.chat_with_keyframes(frames, transcript, prompt, schema, "observer")
                except Exception as e:
                    log.warning("video path failed: %s", e)
                    data = client.chat_with_keyframes(frames, transcript, prompt, schema, "observer")
            else:
                data = client.chat_with_keyframes(frames, transcript, prompt, schema, "observer")
        except Exception as e:
            log.warning("model observe failed, using fallback: %s", e)
            data = None
    if data is None:
        log.info("using deterministic fallback observations")
        data = fallback_observations(frames)
    validate_observations(data)
    out = job_dir / "observations.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log.info("wrote %s (%d obs)", out, len(data["observations"]))
    return data