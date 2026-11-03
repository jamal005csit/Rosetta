"""Export job to zip. AT-14. Only touches generated_app output, never AppSpec."""
import logging
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)

REQUIRED_TOP = ["appspec.json", "report.html", "MIGRATION_NOTES.md"]


def _find_migration(job_dir: Path) -> Path | None:
    a = job_dir / "MIGRATION_NOTES.md"
    if a.exists():
        return a
    b = job_dir / "generated_app" / "MIGRATION_NOTES.md"
    if b.exists():
        return b
    return None


def export_job(job_dir: Path) -> Path:
    job_dir = Path(job_dir)
    appspec = job_dir / "appspec.json"
    report = job_dir / "report.html"
    gdir = job_dir / "generated_app"
    if not appspec.exists():
        raise FileNotFoundError(f"missing {appspec}")
    if not report.exists():
        raise FileNotFoundError(f"missing {report}")
    if not (gdir / "package.json").exists():
        raise FileNotFoundError(f"missing {gdir}/package.json")
    mig = _find_migration(job_dir)
    if mig is None:
        raise FileNotFoundError("missing MIGRATION_NOTES.md")
    out = job_dir / "export.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(gdir.rglob("*")):
            if f.is_file():
                arc = f.relative_to(job_dir)
                z.write(f, arc.as_posix())
        z.write(appspec, "appspec.json")
        z.write(report, "report.html")
        z.write(mig, "MIGRATION_NOTES.md")
    log.info("export %s %d bytes", out, out.stat().st_size)
    return out


def zip_members(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path, "r") as z:
        return z.namelist()