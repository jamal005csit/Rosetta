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


def test_complete_stage_router_is_mounted():
    with tempfile.TemporaryDirectory() as td:
        c = _client_for(td)
        files = {"f": ("demo.mp4", io.BytesIO(b"fake-video-bytes"), "video/mp4")}
        jid = c.post("/jobs", files=files).json()["id"]
        # The complete router is mounted; an unknown stage reaches its validation
        # branch instead of returning 404 from a missing route.
        response = c.post(f"/jobs/{jid}/run/not-a-stage")
        assert response.status_code == 400


def test_evidence_file_endpoint_is_limited_to_frames_and_replay():
    with tempfile.TemporaryDirectory() as td:
        c = _client_for(td)
        files = {"f": ("demo.mp4", io.BytesIO(b"fake-video-bytes"), "video/mp4")}
        jid = c.post("/jobs", files=files).json()["id"]
        frame_dir = Path(td) / jid / "frames"
        frame_dir.mkdir(exist_ok=True)
        (frame_dir / "frame_0001.png").write_bytes(b"test frame")
        response = c.get(f"/jobs/{jid}/files/frames/frame_0001.png")
        assert response.status_code == 200
        assert response.content == b"test frame"
        portable = c.get(f"/jobs/{jid}/frames/frame_0001.png")
        assert portable.status_code == 200 and portable.content == b"test frame"
        assert c.get(f"/jobs/{jid}/files/upload.mp4").status_code == 403
