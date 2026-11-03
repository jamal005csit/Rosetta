import json
from pathlib import Path
import tempfile

from backend.stages.stage2_observe import fallback_observations
from backend.stages.stage3_specify import fallback_appspec, normalize_appspec, validate_appspec, specify_job
import jsonschema

def _job_with_obs(td: str) -> Path:
    jd = Path(td)
    (jd / "frames").mkdir(exist_ok=True)
    obs = fallback_observations([])
    (jd / "observations.json").write_text(json.dumps(obs), encoding="utf-8")
    return jd

def test_appspec_validates_and_evidence():
    with tempfile.TemporaryDirectory() as td:
        jd = _job_with_obs(td)
        data = specify_job(jd, client=None)
        assert (jd / "appspec.json").exists()
        for s in data["screens"]:
            for f in s["fields"]:
                assert f["evidence"], f"field {f['id']} no evidence"
            for sc in s["shortcuts"]:
                assert sc["evidence"]
        for fl in data["flows"]:
            assert fl["evidence"]
        for r in data["rules"]:
            assert r["examples"] and r["examples"][0]["evidence"]
        for j in data["journey"]:
            assert j["legacy_frame"]

def test_coverage_has_archive():
    with tempfile.TemporaryDirectory() as td:
        jd = _job_with_obs(td)
        data = specify_job(jd, client=None)
        items = [c["item"] for c in data["coverage"]["unverified"]]
        assert any("Archive" in i for i in items)

def test_single_example_confidence_cap():
    obs = fallback_observations([])
    data = fallback_appspec(obs)
    # force a bad confidence to prove normalizer clamps
    for r in data["rules"]:
        if len(r["examples"]) == 1:
            r["confidence"] = 0.95
    data = normalize_appspec(data, obs)
    for r in data["rules"]:
        if len(r["examples"]) == 1:
            assert float(r["confidence"]) <= 0.6
    validate_appspec(data)