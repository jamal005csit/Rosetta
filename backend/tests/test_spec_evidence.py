import json
from pathlib import Path
import tempfile

import pytest

from backend.stages.stage3_specify import (
    normalize_appspec,
    specify_job,
    validate_appspec,
)


def _job_with_evidence(td: str) -> tuple[Path, dict]:
    job_dir = Path(td)
    frames = job_dir / "frames"
    frames.mkdir(exist_ok=True)
    (frames / "frame_0001.png").write_bytes(b"real-frame-placeholder-for-unit-test")
    observations = {
        "observations": [
            {"t": 1.0, "action": "click", "target_label": "Login",
             "frame": "frames/frame_0001.png", "frame_timestamp": 1.0,
             "screen_after": {"title": "Home"}}
        ]
    }
    (job_dir / "observations.json").write_text(json.dumps(observations), encoding="utf-8")
    return job_dir, observations


def _valid_appspec() -> dict:
    return {
        "app": {"name": "Observed App", "domain": "demo", "language": "en", "direction": "ltr"},
        "screens": [{
            "id": "scr_home", "title": "Home", "evidence": ["t=1.0s"],
            "fields": [{
                "id": "fld_login", "label": "Login", "type": "button",
                "required": False, "enabled": True, "evidence": ["t=1.0s"]
            }],
            "shortcuts": []
        }],
        "flows": [],
        "rules": [],
        "sample_data": {},
        "journey": [{
            "step": 1, "weight": 1, "action": "click", "target": "fld_login",
            "value": None,
            "expect": {"screen": "scr_home", "values": {}, "messages": []},
            "legacy_frame": "frames/frame_0001.png"
        }],
        "coverage": {"unverified": []}
    }


class FakeSpecifier:
    def chat_json(self, prompt, schema, label):
        return _valid_appspec()


def test_appspec_requires_real_observation_and_frame_evidence():
    with tempfile.TemporaryDirectory() as td:
        job_dir, observations = _job_with_evidence(td)
        data = specify_job(job_dir, client=FakeSpecifier())
        assert (job_dir / "appspec.json").is_file()
        validate_appspec(data, observations, job_dir)
        assert data["journey"][0]["legacy_frame"] == "frames/frame_0001.png"


def test_specification_refuses_offline_hardcoded_fallback():
    with tempfile.TemporaryDirectory() as td:
        job_dir, _ = _job_with_evidence(td)
        with pytest.raises(RuntimeError, match="Refusing to emit a hard-coded"):
            specify_job(job_dir, client=None)


def test_single_example_confidence_is_capped_without_fabricating_evidence():
    data = _valid_appspec()
    data["rules"] = [{
        "id": "rule_one", "kind": "calculation", "description": "Observed rule",
        "examples": [{"inputs": {"x": 1}, "output": "1", "evidence": ["t=1.0s"]}],
        "confidence": 0.95
    }]
    normalized = normalize_appspec(data, {"observations": [{"t": 1.0}]})
    assert normalized["rules"][0]["confidence"] == 0.6
    assert normalized["rules"][0]["examples"][0]["evidence"] == ["t=1.0s"]


def test_invalid_evidence_timestamp_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        job_dir, observations = _job_with_evidence(td)
        data = _valid_appspec()
        data["screens"][0]["fields"][0]["evidence"] = ["t=99.0s"]
        with pytest.raises(ValueError, match="not present in observations"):
            validate_appspec(data, observations, job_dir)


def test_journey_cannot_reference_nonexistent_or_unobserved_frame():
    with tempfile.TemporaryDirectory() as td:
        job_dir, observations = _job_with_evidence(td)
        data = _valid_appspec()
        data["journey"][0]["legacy_frame"] = "frames/frame_9999.png"
        with pytest.raises(ValueError, match="not attached to an observation"):
            validate_appspec(data, observations, job_dir)
