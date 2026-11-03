import json
from pathlib import Path
import tempfile
import zipfile

from backend.stages.stage2_observe import fallback_observations
from backend.stages.stage3_specify import fallback_appspec, normalize_appspec
from backend.stages.stage4_generate import generate_job
from backend.stages.stage5_replay import replay_job
from backend.stages.stage6_score import score_job
from backend.stages.stage6_repair import repair_job
from backend.stages.stage6_report import generate_report
from backend.export.packager import export_job, zip_members


def test_export_contains_required():
    with tempfile.TemporaryDirectory() as td:
        jd = Path(td)
        (jd / "frames").mkdir(exist_ok=True)
        obs = fallback_observations([])
        spec = normalize_appspec(fallback_appspec(obs), obs)
        (jd / "appspec.json").write_text(json.dumps(spec), encoding="utf-8")
        generate_job(jd, client=None)
        replay_job(jd)
        score_job(jd, client=None)
        repair_job(jd, client=None, max_rounds=3)
        generate_report(jd)
        z = export_job(jd)
        assert z.exists()
        members = zip_members(z)
        assert "appspec.json" in members
        assert "report.html" in members
        assert "MIGRATION_NOTES.md" in members
        assert any(m.startswith("generated_app/") for m in members)
        assert any("package.json" in m for m in members)
        with zipfile.ZipFile(z, "r") as zh:
            assert json.loads(zh.read("appspec.json"))
            assert b"Parity" in zh.read("report.html")