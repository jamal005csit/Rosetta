import json
from pathlib import Path
import tempfile

from backend.stages.stage2_observe import fallback_observations
from backend.stages.stage3_specify import fallback_appspec, normalize_appspec
from backend.stages.stage4_generate import generate_job

def _make_job(td: str) -> Path:
    jd = Path(td)
    (jd / "frames").mkdir(exist_ok=True)
    obs = fallback_observations([])
    spec = normalize_appspec(fallback_appspec(obs), obs)
    (jd / "appspec.json").write_text(json.dumps(spec), encoding="utf-8")
    return jd

def test_generate_serves_and_seed():
    with tempfile.TemporaryDirectory() as td:
        jd = _make_job(td)
        out = generate_job(jd, client=None)
        assert out["screens"] >= 5
        g = jd / "generated_app"
        pkg = json.loads((g / "package.json").read_text(encoding="utf-8"))
        assert "start" in pkg["scripts"]
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        assert "express" in deps and "better-sqlite3" in deps
        assert "react" in deps and "vite" in deps
        srv = (g / "server/index.js").read_text(encoding="utf-8")
        assert "better-sqlite3" in (g / "server/db.js").read_text(encoding="utf-8") or "better-sqlite3" in srv
        assert "express" in srv and "PORT" in srv and "listen" in srv
        seed = json.loads((g / "data/seed.json").read_text(encoding="utf-8"))
        assert "customers" in seed and len(seed["customers"]) >= 2
        assert "items" in seed and len(seed["items"]) >= 2
        spec = json.loads((jd / "appspec.json").read_text(encoding="utf-8"))
        blob = ""
        for p in (g / "client/src").rglob("*.tsx"):
            blob += p.read_text(encoding="utf-8")
        blob += (g / "dist/index.html").read_text(encoding="utf-8")
        for s in spec["screens"]:
            for f in s["fields"]:
                assert f["id"] in blob, f"missing testid {f['id']}"
        app_tsx = (g / "client/src/App.tsx").read_text(encoding="utf-8")
        order_tsx = (g / "client/src/screens/Order.tsx").read_text(encoding="utf-8")
        assert "F2" in order_tsx and "F5" in order_tsx and "Escape" in order_tsx
        rules = (g / "client/src/lib/rules.ts").read_text(encoding="utf-8")
        assert "0.14" in rules and "0.05" in rules and "0.12" in rules
        assert (g / "MIGRATION_NOTES.md").exists()
        assert (g / "dist/index.html").exists()

def test_shortcuts_preserved():
    with tempfile.TemporaryDirectory() as td:
        jd = _make_job(td)
        generate_job(jd, client=None)
        dist = (jd / "generated_app/dist/index.html").read_text(encoding="utf-8")
        assert "F2" in dist and "F5" in dist and "Escape" in dist