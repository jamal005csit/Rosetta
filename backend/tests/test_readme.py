import re
from pathlib import Path


def test_readme_documents_real_windows_pipeline():
    readme = Path(__file__).resolve().parents[2] / "README.md"
    assert readme.is_file()
    text = readme.read_text(encoding="utf-8")
    required = [
        "PowerShell",
        "py -3.11 -m venv .venv",
        "python -m playwright install chromium",
        "META_API_BASE",
        "META_API_KEY",
        "MUSE_MODEL",
        "MAX_CALLS_PER_JOB",
        "WHISPER_MODEL",
        "npm install",
        "npm start",
        "Run full pipeline",
        "report.html",
        "export.zip",
        "legacy_app",
        "generated_app",
        "python -m pytest backend/tests",
    ]
    for phrase in required:
        assert phrase in text, f"README missing {phrase}"
    assert "offline fallback works" not in text.lower()

    numbered_steps = [
        line for line in text.splitlines()
        if re.match(r"^\d+\.\s", line.strip())
    ]
    assert 5 <= len(numbered_steps) <= 9, (
        f"setup guide must stay under 10 steps, found {len(numbered_steps)}"
    )
