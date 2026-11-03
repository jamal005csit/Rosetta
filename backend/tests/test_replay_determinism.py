import json
from pathlib import Path
import tempfile

import pytest

from backend.tests.appspec_fixture import build_appspec
from backend.stages import stage5_replay


def _job(td: str) -> Path:
    job_dir = Path(td)
    frames = job_dir / "frames"
    frames.mkdir(exist_ok=True)
    for number in range(1, 9):
        (frames / f"frame_{number:04d}.png").write_bytes(b"test-only legacy image fixture")
    (job_dir / "appspec.json").write_text(json.dumps(build_appspec()), encoding="utf-8")
    return job_dir


def test_replay_fails_closed_when_generated_app_cannot_start(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        job_dir = _job(td)

        def unavailable(_job_dir):
            raise RuntimeError("generated app unavailable in unit test")

        monkeypatch.setattr(stage5_replay, "_start_server", unavailable)
        with pytest.raises(RuntimeError, match="generated app unavailable"):
            stage5_replay.replay_job(job_dir)

        replay_dir = job_dir / "replay"
        assert not (replay_dir / "steps.json").exists()
        assert not list(replay_dir.glob("new_step_*.png"))
        assert not list(replay_dir.glob("dom_step_*.html"))
