"""P6 media ingestion: real keyframes and optional local speech transcription."""
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)
_SHOWINFO_TIME = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")


def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _extract_frames(video: Path, frames_dir: Path, filter_value: str) -> tuple[list[Path], list[float]]:
    output = str(frames_dir / "frame_%04d.png")
    command = [
        "ffmpeg", "-hide_banner", "-y", "-i", str(video),
        "-vf", filter_value, "-vsync", "vfr", output,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    frames = sorted(frames_dir.glob("frame_*.png"))
    times = [float(value) for value in _SHOWINFO_TIME.findall(result.stderr)]
    if result.returncode != 0:
        log.warning("ffmpeg frame extraction failed: %s", result.stderr[-1000:])
    return frames, times


def extract_keyframes(video: Path, frames_dir: Path) -> list[Path]:
    if not have_ffmpeg():
        raise RuntimeError("ffmpeg is required to extract recording keyframes")
    if not video.is_file():
        raise FileNotFoundError(f"recording not found: {video}")
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old_frame in frames_dir.glob("frame_*.png"):
        old_frame.unlink()

    frames, timestamps = _extract_frames(video, frames_dir, "select='gt(scene,0.3)',showinfo")
    if not frames:
        log.warning("scene detection produced no frames; retrying at 1 frame per second")
        frames, timestamps = _extract_frames(video, frames_dir, "fps=1,showinfo")
    if not frames:
        raise RuntimeError("ffmpeg could not extract any keyframes from the recording")

    # ffmpeg's showinfo reports one timestamp per emitted frame. Keep only a
    # one-to-one mapping; never fabricate timestamps when the counts disagree.
    if len(timestamps) != len(frames):
        log.warning("frame/timestamp count mismatch (%d frames, %d timestamps)", len(frames), len(timestamps))
        timestamp_rows = []
    else:
        timestamp_rows = [
            {"frame": frame.name, "t": timestamp}
            for frame, timestamp in zip(frames, timestamps)
        ]
    (frames_dir.parent / "frame_timestamps.json").write_text(
        json.dumps(timestamp_rows, indent=2), encoding="utf-8"
    )
    log.info("extracted %d frames", len(frames))
    return frames


def extract_transcript(video: Path, job_dir: Path) -> str:
    transcript_path = job_dir / "transcript.txt"
    if not have_ffmpeg():
        raise RuntimeError("ffmpeg is required to extract audio for transcription")
    wav_path = job_dir / "audio.wav"
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-y", "-i", str(video), "-vn", "-ar", "16000",
         "-ac", "1", str(wav_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not wav_path.is_file() or wav_path.stat().st_size == 0:
        transcript_path.write_text("", encoding="utf-8")
        log.info("no audio track extracted; transcript is empty")
        return ""

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        transcript_path.write_text("", encoding="utf-8")
        log.warning("faster-whisper is not installed; audio transcript unavailable")
        return ""

    model_name = os.getenv("WHISPER_MODEL", "tiny")
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(str(wav_path), vad_filter=True)
    transcript = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
    transcript_path.write_text(transcript, encoding="utf-8")
    log.info("transcribed audio using faster-whisper model=%s chars=%d", model_name, len(transcript))
    return transcript


def ingest(job_dir: Path) -> dict:
    job_dir = Path(job_dir)
    video = job_dir / "upload.mp4"
    frames = extract_keyframes(video, job_dir / "frames")
    transcript = extract_transcript(video, job_dir)
    return {
        "frames": [str(frame) for frame in frames],
        "transcript": transcript,
        "transcript_available": bool(transcript.strip()),
    }
