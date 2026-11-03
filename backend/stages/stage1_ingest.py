"""P6 fallback: ffmpeg scene keyframes + audio transcript. Always built."""
import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

def extract_keyframes(video: Path, frames_dir: Path) -> list[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    for p in frames_dir.glob("frame_*.png"):
        p.unlink()
    if not have_ffmpeg():
        log.warning("ffmpeg missing, writing placeholder frame list empty")
        return []
    cmd = ["ffmpeg", "-y", "-i", str(video),
           "-filter:v", "select='gt(scene,0.3)',showinfo",
           "-vsync", "vfr", str(frames_dir / "frame_%04d.png")]
    log.info("run: %s", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log.warning("scene extract failed: %s, fallback to 1fps", r.stderr[-500:])
        cmd2 = ["ffmpeg", "-y", "-i", str(video), "-vf", "fps=1",
                str(frames_dir / "frame_%04d.png")]
        subprocess.run(cmd2, capture_output=True)
    frames = sorted(frames_dir.glob("frame_*.png"))
    log.info("extracted %d frames", len(frames))
    return frames

def extract_transcript(video: Path, job_dir: Path) -> str:
    out = job_dir / "transcript.txt"
    if not have_ffmpeg():
        out.write_text("", encoding="utf-8")
        return ""
    wav = job_dir / "audio.wav"
    subprocess.run(["ffmpeg", "-y", "-i", str(video), "-ar", "16000",
                    "-ac", "1", str(wav)], capture_output=True)
    # Offline-safe: no STT dependency in Phase 1; leave hook for Muse Voice later.
    txt = ""
    if wav.exists():
        log.info("audio extracted %d bytes, transcript left empty (hook for STT)", wav.stat().st_size)
    out.write_text(txt, encoding="utf-8")
    return txt

def ingest(job_dir: Path) -> dict:
    video = job_dir / "upload.mp4"
    frames = extract_keyframes(video, job_dir / "frames")
    transcript = extract_transcript(video, job_dir)
    return {"frames": [str(p) for p in frames], "transcript": transcript}