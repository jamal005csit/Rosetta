"""Create a clean, reproducible evidence and generated-app export ZIP."""
import logging
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)

REQUIRED_FILES = (
    "appspec.json",
    "report.html",
    "parity.json",
    "generated_app/package.json",
    "generated_app/dist/index.html",
)


def _migration_file(job_dir: Path) -> Path | None:
    root_copy = job_dir / "MIGRATION_NOTES.md"
    if root_copy.is_file():
        return root_copy
    generated_copy = job_dir / "generated_app" / "MIGRATION_NOTES.md"
    return generated_copy if generated_copy.is_file() else None


def _excluded(path: Path) -> bool:
    if path.is_symlink():
        return True
    if any(part in {"node_modules", ".git", "__pycache__", ".pytest_cache"} for part in path.parts):
        return True
    if path.suffix.lower() in {".db", ".mp4", ".mov", ".mkv", ".webm", ".wav", ".pyc", ".tmp"}:
        return True
    if path.name == ".env" or path.name.startswith(".env."):
        return True
    return False


def _add_file(archive: zipfile.ZipFile, job_dir: Path, path: Path, arcname: str) -> None:
    resolved = path.resolve()
    if not resolved.is_relative_to(job_dir.resolve()) or not resolved.is_file() or _excluded(path):
        return
    archive.write(resolved, arcname)


def export_job(job_dir: Path) -> Path:
    job_dir = Path(job_dir).resolve()
    generated_dir = job_dir / "generated_app"
    for relative in REQUIRED_FILES:
        required = job_dir / relative
        if not required.is_file():
            raise FileNotFoundError(f"required export artifact is missing: {relative}")

    migration = _migration_file(job_dir)
    if migration is None:
        raise FileNotFoundError("required export artifact is missing: MIGRATION_NOTES.md")

    output = job_dir / "export.zip"
    output.unlink(missing_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        # Include source, built Vite assets, seed data, and lockfiles, but never
        # node_modules, runtime databases, uploaded recordings, or secrets.
        for path in sorted(generated_dir.rglob("*")):
            if path.is_file():
                _add_file(
                    archive, job_dir, path,
                    path.relative_to(job_dir).as_posix(),
                )

        root_artifacts = (
            "appspec.json",
            "observations.json",
            "frame_timestamps.json",
            "transcript.txt",
            "parity.json",
            "repair_history.json",
            "report.html",
        )
        for relative in root_artifacts:
            path = job_dir / relative
            if path.is_file():
                _add_file(archive, job_dir, path, relative)

        # Preserve original keyframes and real browser captures for auditability.
        for folder in ("frames", "replay"):
            directory = job_dir / folder
            if not directory.is_dir():
                continue
            for path in sorted(directory.rglob("*")):
                if path.is_file() and path.suffix.lower() in {".png", ".html", ".json"}:
                    _add_file(
                        archive, job_dir, path,
                        path.relative_to(job_dir).as_posix(),
                    )

        if migration.resolve() != (job_dir / "MIGRATION_NOTES.md").resolve():
            _add_file(archive, job_dir, migration, "MIGRATION_NOTES.md")

    log.info("exported %s (%d bytes)", output, output.stat().st_size)
    return output


def zip_members(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path, "r") as archive:
        return archive.namelist()
