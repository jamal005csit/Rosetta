import json
from pathlib import Path
import tempfile

import jsonschema
import pytest

from backend.tests.appspec_fixture import build_appspec
from backend.stages.stage4_generate import generate_job
from backend.stages.stage5_replay import replay_job
from backend.stages.stage6_score import score_job
from backend.stages.stage6_repair import repair_job
from backend.stages.stage6_report import generate_report


def _demo_job(td: str) -> Path:
    job_dir = Path(td)
    frames = job_dir / "frames"
    replay_dir = job_dir / "replay"
    frames.mkdir(exist_ok=True)
    replay_dir.mkdir(exist_ok=True)
    spec = build_appspec()
    (job_dir / "appspec.json").write_text(json.dumps(spec), encoding="utf-8")
    replay_rows = []
    for journey_step in spec["journey"]:
        number = journey_step["step"]
        legacy = job_dir / journey_step["legacy_frame"]
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_bytes(b"test-only legacy frame fixture")
        screenshot_name = f"new_step_{number:02d}.png"
        snapshot_name = f"snapshot_step_{number:02d}.json"
        (replay_dir / screenshot_name).write_bytes(b"test-only browser screenshot fixture")
        snapshot = {
            "active_screen": journey_step["expect"]["screen"],
            "text": "",
            "fields": {},
            "title": "test fixture",
            "url": "http://test.invalid"
        }
        (replay_dir / snapshot_name).write_text(json.dumps(snapshot), encoding="utf-8")
        replay_rows.append({
            "step": number, "success": True, "active_screen": snapshot["active_screen"],
            "screenshot": screenshot_name, "snapshot": snapshot_name,
            "dom": f"dom_step_{number:02d}.html", "error": None
        })
    (replay_dir / "steps.json").write_text(json.dumps(replay_rows), encoding="utf-8")
    return job_dir


def _parity_schema() -> dict:
    p = Path(__file__).resolve().parents[1] / "schemas" / "parity.schema.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_score_stores_frames_verdict_reason():
    with tempfile.TemporaryDirectory() as td:
        jd = _demo_job(td)
        par = score_job(jd, client=None)
        jsonschema.validate(par, _parity_schema())
        assert (jd / "parity.json").exists()
        assert len(par["steps"]) >= 1
        for s in par["steps"]:
            assert s["legacy_frame"] and s["new_screenshot"] and s["verdict"] and s["reason"]
            assert s["visual"] == 0.0  # no model judge means no visual credit
            assert s["action_success"] is True
            assert (jd / s["legacy_frame"]).exists()
            assert (jd / s["new_screenshot"]).exists()
            assert s["legacy_frame"].split("/")[-1] in s["reason"]
            assert s["new_screenshot"].split("/")[-1] in s["reason"]


def test_repair_fails_closed_without_muse_and_preserves_appspec():
    with tempfile.TemporaryDirectory() as td:
        job_dir = _demo_job(td)
        spec_before = (job_dir / "appspec.json").read_text(encoding="utf-8")
        replay_path = job_dir / "replay" / "steps.json"
        replay_rows = json.loads(replay_path.read_text(encoding="utf-8"))
        replay_rows[0]["active_screen"] = "scr_wrong"
        replay_path.write_text(json.dumps(replay_rows), encoding="utf-8")

        with pytest.raises(RuntimeError, match="configured Muse client"):
            repair_job(job_dir, client=None, max_rounds=3)

        assert (job_dir / "appspec.json").read_text(encoding="utf-8") == spec_before
        assert not (job_dir / "repair_history.json").exists()


def test_repair_stops_when_parity_already_passes():
    with tempfile.TemporaryDirectory() as td:
        job_dir = _demo_job(td)
        result = repair_job(job_dir, client=None, max_rounds=3)
        assert result["rounds"] == 0
        assert result["pass"] is True
        assert result["history"] == []


def test_report_shows_all_sections():
    with tempfile.TemporaryDirectory() as td:
        jd = _demo_job(td)
        score_job(jd, client=None)
        repair_job(jd, client=None, max_rounds=3)
        rp = generate_report(jd)
        assert rp.exists()
        h = rp.read_text(encoding="utf-8")
        assert "Parity:" in h and "Per-step table" in h
        assert "Coverage ledger" in h
        assert "Repair history" in h and "Unresolved issues" in h