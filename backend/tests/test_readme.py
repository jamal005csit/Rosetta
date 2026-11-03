import re
from pathlib import Path


def test_readme_under_10_steps():
    p = Path(__file__).resolve().parents[2] / "README.md"
    assert p.exists(), "README.md missing"
    txt = p.read_text(encoding="utf-8")
    for needle in ["META_API_BASE", "MUSE_MODEL", "npm install", "npm start",
                   "report.html", "export.zip", "legacy_app", "generated_app"]:
        assert needle in txt, f"README missing {needle}"
    steps = [l for l in txt.splitlines() if re.match(r"^\d+\.\s", l.strip())]
    assert 5 <= len(steps) <= 9, f"demo must be under 10 steps, found {len(steps)}"