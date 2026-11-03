import json
from pathlib import Path
import tempfile

from backend.tests.appspec_fixture import build_appspec
from backend.stages.stage4_generate import generate_job

def _make_job(td: str) -> Path:
    job_dir = Path(td)
    (job_dir / "frames").mkdir(exist_ok=True)
    spec = build_appspec()
    (job_dir / "appspec.json").write_text(json.dumps(spec), encoding="utf-8")
    return job_dir

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
        for s in spec["screens"]:
            for f in s["fields"]:
                assert f["id"] in blob, f"missing testid {f['id']}"
        app_tsx = (g / "client/src/App.tsx").read_text(encoding="utf-8")
        order_tsx = (g / "client/src/screens/Order.tsx").read_text(encoding="utf-8")
        assert "F2" in order_tsx and "F5" in order_tsx and "Escape" in order_tsx
        assert "Save failed:" in order_tsx
        assert "catch { setMsg('Saved total" not in order_tsx
        rules = (g / "client/src/lib/rules.ts").read_text(encoding="utf-8")
        assert "0.14" in rules and "0.05" in rules and "0.12" in rules
        assert (g / "MIGRATION_NOTES.md").exists()
        assert (g / "client/index.html").exists()
        assert not (g / "dist/index.html").exists()
        assert "npm run build" in pkg["scripts"]["start"]
        vite = (g / "vite.config.ts").read_text(encoding="utf-8")
        assert "root: 'client'" in vite and "outDir: '../dist'" in vite
        server = (g / "server/index.js").read_text(encoding="utf-8")
        assert "Generated React frontend is not built" in server

def test_shortcuts_preserved():
    with tempfile.TemporaryDirectory() as td:
        jd = _make_job(td)
        generate_job(jd, client=None)
        order = (jd / "generated_app/client/src/screens/Order.tsx").read_text(encoding="utf-8")
        assert "F2" in order and "F5" in order and "Escape" in order
def test_muse_generation_failure_does_not_silently_use_template():
    class BrokenMuse:
        def chat_json(self, *args, **kwargs):
            raise RuntimeError("provider unavailable")

    from backend.stages.stage4_generate import _one_screen
    import pytest

    with pytest.raises(RuntimeError, match="Muse screen generation failed"):
        _one_screen({"id": "scr_custom", "title": "Custom", "fields": []}, BrokenMuse())

