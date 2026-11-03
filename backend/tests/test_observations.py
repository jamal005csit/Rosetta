import json
from pathlib import Path
import tempfile

from backend.muse.client import MuseClient
from backend.muse.budget import CallBudget
from backend.stages.stage2_observe import observations_schema, observe_job
import jsonschema

PNG = b"\x89PNG\r\n\x1a\n"

def _transport(payload: dict) -> dict:
    import json as j
    data = {"observations": [{"t": 4.2, "action": "click", "target_label": "Login",
             "screen_after": {"title": "Main menu"}}]}
    return {"choices": [{"message": {"content": j.dumps(data)}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5}}

def test_observe_validates_and_timestamps():
    with tempfile.TemporaryDirectory() as td:
        jd = Path(td)
        (jd / "frames").mkdir()
        (jd / "frames" / "frame_0001.png").write_bytes(PNG)
        (jd / "transcript.txt").write_text("hello", encoding="utf-8")
        client = MuseClient("https://api.meta.ai/v1", "k", "muse-spark-1.3",
                            jd, CallBudget(10), transport=_transport)
        data = observe_job(jd, client=client)
        jsonschema.validate(data, observations_schema())
        assert all(isinstance(o["t"], (int, float)) for o in data["observations"])
        assert (jd / "observations.json").exists()
        assert (jd / "muse_calls.jsonl").exists()

def test_observe_fallback_offline():
    with tempfile.TemporaryDirectory() as td:
        jd = Path(td)
        (jd / "frames").mkdir()
        data = observe_job(jd, client=None)
        assert len(data["observations"]) >= 1
        assert all("t" in o for o in data["observations"])