"""Stage 2: derive observations only from supplied recording evidence."""
import json
import logging
from pathlib import Path

import jsonschema

from backend.muse.client import MuseClient
from backend.stages import stage1_ingest

log = logging.getLogger(__name__)


def observations_schema() -> dict:
    path = Path(__file__).resolve().parents[1] / "schemas" / "observations.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def prompts_observer() -> str:
    path = Path(__file__).resolve().parents[1] / "prompts" / "observer.md"
    return path.read_text(encoding="utf-8")


def validate_observations(data: dict) -> None:
    jsonschema.validate(instance=data, schema=observations_schema())
    observations = data["observations"]
    timestamps = [float(item["t"]) for item in observations]
    if timestamps != sorted(timestamps):
        raise ValueError("observation timestamps must be in chronological order")
    if len(timestamps) != len(set(timestamps)):
        raise ValueError("observation timestamps must be unique")


def observe_job(job_dir: Path, client: MuseClient | None = None) -> dict:
    job_dir = Path(job_dir)
    if client is None:
        raise RuntimeError(
            "Observation requires a configured Muse client. Refusing to invent actions "
            "when no model is available; configure META_API_KEY and retry."
        )

    video = job_dir / "upload.mp4"
    frames_dir = job_dir / "frames"
    frames = sorted(frames_dir.glob("frame_*.png")) if frames_dir.is_dir() else []
    transcript_path = job_dir / "transcript.txt"
    transcript = transcript_path.read_text(encoding="utf-8") if transcript_path.is_file() else ""

    if video.is_file() and not frames:
        ingest_result = stage1_ingest.ingest(job_dir)
        frames = [Path(item) for item in ingest_result["frames"]]
        transcript = ingest_result.get("transcript", transcript)
    if not frames:
        raise RuntimeError(
            "No usable keyframes were extracted. Check that the uploaded recording is valid "
            "and ffmpeg is installed; no synthetic observations were generated."
        )

    prompt = prompts_observer()
    timestamp_path = job_dir / "frame_timestamps.json"
    frame_timestamps = []
    if timestamp_path.is_file():
        frame_timestamps = json.loads(timestamp_path.read_text(encoding="utf-8"))
    if frame_timestamps:
        prompt += "\n\nExtracted frame references (filename and exact video timestamp):\n"
        prompt += json.dumps(frame_timestamps, ensure_ascii=False)

    # Always use the validated keyframe path. The raw-video path previously bypassed
    # schema retries and could return unvalidated or fabricated output.
    data = client.chat_with_keyframes(frames, transcript, prompt, observations_schema(), "observer")
    validate_observations(data)
    if frame_timestamps:
        for observation in data["observations"]:
            nearest = min(frame_timestamps, key=lambda row: abs(float(row["t"]) - float(observation["t"])))
            if abs(float(nearest["t"]) - float(observation["t"])) <= 3.0:
                observation["frame"] = nearest["frame"]
                observation["frame_timestamp"] = float(nearest["t"])

    output = job_dir / "observations.json"
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("wrote %s (%d evidence-backed observations)", output, len(data["observations"]))
    return data
