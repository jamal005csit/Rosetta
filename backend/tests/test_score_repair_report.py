import json
from pathlib import Path
import tempfile

import jsonschema

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
            assert (jd / s["legacy_frame"]).exists()
            assert (jd / s["new_screenshot"]).exists()
            assert s["legacy_frame"].split("/")[-1] in s["reason"]
            assert s["new_screenshot"].split("/")[-1] in s["reason"]


def test_repair_loop_stops_and_reruns_all():
    with tempfile.TemporaryDirectory() as td:
        jd = _demo_job(td)
        spec_before = (jd / "appspec.json").read_text(encoding="utf-8")
        dist = jd / "generated_app" / "dist" / "index.html"
        html = dist.read_text(encoding="utf-8")
        # break State: remove a screen section
        html2 = html.replace('id="scr_order"', 'id="scr_order_BROKEN"')
        assert html2 != html
        dist.write_text(html2, encoding="utf-8")
        bad = score_job(jd, client=None)
        assert any(s["state"] < 1.0 for s in bad["steps"])
        rep = repair_job(jd, client=None, max_rounds=3)
        assert rep["rounds"] <= 3
        assert (jd / "repair_history.json").exists()
        assert rep["rounds"] >= 1
        for r in rep["history"]:
            assert r["reran_all"] is True
            assert r["steps_reran"] == len(json.loads(spec_before)["journey"])
        final = json.loads((jd / "parity.json").read_text(encoding="utf-8"))
        assert final["parity"] >= 90
        assert (jd / "appspec.json").read_text(encoding="utf-8") == spec_before


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