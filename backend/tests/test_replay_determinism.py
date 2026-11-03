import json
from pathlib import Path
import tempfile

from backend.stages.stage2_observe import fallback_observations
from backend.stages.stage3_specify import fallback_appspec, normalize_appspec
from backend.stages.stage4_generate import generate_job
from backend.stages.stage5_replay import replay_job

def _job(td: str) -> Path:
    jd = Path(td)
    (jd / "frames").mkdir(exist_ok=True)
    obs = fallback_observations([])
    spec = normalize_appspec(fallback_appspec(obs), obs)
    (jd / "appspec.json").write_text(json.dumps(spec), encoding="utf-8")
    generate_job(jd, client=None)
    return jd

def test_replay_shots_dom_and_determinism():
    with tempfile.TemporaryDirectory() as td:
        jd = _job(td)
        s1 = replay_job(jd)
        s2 = replay_job(jd)
        assert s1 == s2, "two runs must give identical step lists"
        assert len(s1) >= 1
        spec = json.loads((jd / "appspec.json").read_text(encoding="utf-8"))
        assert len(s1) == len(spec["journey"])
        for st in s1:
            shot = jd / "replay" / st["screenshot"]
            dom = jd / "replay" / st["dom"]
            assert shot.exists() and shot.stat().st_size > 0
            assert dom.exists() and st["target"] in dom.read_text(encoding="utf-8")