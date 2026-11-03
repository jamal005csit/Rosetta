import io
import os
from pathlib import Path
import tempfile

from fastapi.testclient import TestClient


def _client_for(tmp: str):
    os.environ["JOBS_DIR"] = tmp
    from backend.app.main import app
    return TestClient(app)


def test_upload_list_status_delete():
    with tempfile.TemporaryDirectory() as td:
        c = _client_for(td)
        assert c.get("/health").json() == {"ok": True}
        files = {"f": ("demo.mp4", io.BytesIO(b"fake-video-bytes"), "video/mp4")}
        r = c.post("/jobs", files=files)
        assert r.status_code == 200
        jid = r.json()["id"]
        lst = c.get("/jobs").json()
        assert jid in lst["jobs"]
        st = c.get(f"/jobs/{jid}/status").json()
        assert "stages" in st and "ingest" in st["stages"]
        ev = c.get(f"/jobs/{jid}/events")
        assert ev.status_code == 200
        assert "text/event-stream" in ev.headers["content-type"]
        d = c.delete(f"/jobs/{jid}")
        assert d.status_code == 200
        assert c.get("/jobs").json() == {"jobs": []}


def test_full_pipeline_via_api_then_export_and_report():
    with tempfile.TemporaryDirectory() as td:
        c = _client_for(td)
        files = {"f": ("demo.mp4", io.BytesIO(b"fake-video-bytes"), "video/mp4")}
        jid = c.post("/jobs", files=files).json()["id"]
        for stage in ["observe", "specify", "generate", "replay", "score", "repair", "report"]:
            r = c.post(f"/jobs/{jid}/run/{stage}")
            assert r.status_code == 200, f"{stage} {r.text}"
        assert c.get(f"/jobs/{jid}/parity.json").status_code == 200
        assert c.get(f"/jobs/{jid}/appspec.json").status_code == 200
        rep = c.get(f"/jobs/{jid}/report.html")
        assert rep.status_code == 200 and "Parity" in rep.text
        z = c.get(f"/jobs/{jid}/export.zip")
        assert z.status_code == 200
        import zipfile, io as _io
        names = zipfile.ZipFile(_io.BytesIO(z.content)).namelist()
        assert "appspec.json" in names
        assert "report.html" in names
        assert "MIGRATION_NOTES.md" in names
        assert any(n.startswith("generated_app/") for n in names)