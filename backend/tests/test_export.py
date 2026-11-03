import json
from pathlib import Path
import tempfile
import zipfile

from backend.export.packager import export_job, zip_members


def test_export_contains_built_app_and_evidence_but_excludes_runtime_secrets():
    with tempfile.TemporaryDirectory() as td:
        job_dir = Path(td)
        generated = job_dir / "generated_app"
        (generated / "dist").mkdir(parents=True)
        (generated / "client" / "src").mkdir(parents=True)
        (generated / "node_modules" / "dependency").mkdir(parents=True)
        (generated / "data").mkdir(parents=True)
        (job_dir / "frames").mkdir()
        (job_dir / "replay").mkdir()

        (job_dir / "appspec.json").write_text('{"app":{"name":"Fixture"}}', encoding="utf-8")
        (job_dir / "report.html").write_text("<h1>Parity: 95</h1>", encoding="utf-8")
        (job_dir / "observations.json").write_text('{"observations":[]}', encoding="utf-8")
        (job_dir / "parity.json").write_text('{"parity":95,"pass":true,"steps":[]}', encoding="utf-8")
        (job_dir / "repair_history.json").write_text('{"rounds":0,"history":[]}', encoding="utf-8")
        (job_dir / "upload.mp4").write_bytes(b"private source recording")
        (generated / "package.json").write_text('{"scripts":{"start":"node server/index.js"}}', encoding="utf-8")
        (generated / "dist" / "index.html").write_text("<div id='root'>built</div>", encoding="utf-8")
        (generated / "client" / "src" / "App.tsx").write_text("export default function App() {}", encoding="utf-8")
        (generated / "MIGRATION_NOTES.md").write_text("# Migration notes", encoding="utf-8")
        (generated / "node_modules" / "dependency" / "secret.txt").write_text("exclude", encoding="utf-8")
        (generated / "data" / "app.db").write_bytes(b"runtime database")
        (job_dir / "frames" / "frame_0001.png").write_bytes(b"legacy frame")
        (job_dir / "replay" / "new_step_01.png").write_bytes(b"browser screenshot")

        archive_path = export_job(job_dir)
        assert archive_path.is_file()
        members = zip_members(archive_path)
        assert "appspec.json" in members
        assert "report.html" in members
        assert "MIGRATION_NOTES.md" in members
        assert "generated_app/package.json" in members
        assert "generated_app/dist/index.html" in members
        assert "generated_app/client/src/App.tsx" in members
        assert "observations.json" in members
        assert "parity.json" in members
        assert "frames/frame_0001.png" in members
        assert "replay/new_step_01.png" in members
        assert not any("node_modules" in member for member in members)
        assert not any(member.endswith(".db") for member in members)
        assert not any(member.endswith(".mp4") for member in members)

        with zipfile.ZipFile(archive_path, "r") as archive:
            assert json.loads(archive.read("appspec.json"))
            assert b"Parity" in archive.read("report.html")
