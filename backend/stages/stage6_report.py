"""Report: overall score, per-step table, coverage, repair history, unresolved. FR-15."""
import html
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def _load(job_dir: Path, name: str, default: object) -> object:
    p = Path(job_dir) / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        log.warning("%s read failed: %s", name, e)
        return default


def generate_report(job_dir: Path) -> Path:
    job_dir = Path(job_dir)
    if not (job_dir / "appspec.json").is_file():
        raise FileNotFoundError("appspec.json is required before report generation")
    if not (job_dir / "parity.json").is_file():
        raise FileNotFoundError("parity.json is required before report generation")
    spec = _load(job_dir, "appspec.json", {})
    parity = _load(job_dir, "parity.json", {})
    repair = _load(job_dir, "repair_history.json", {"rounds": 0, "history": []})
    assert isinstance(spec, dict) and isinstance(parity, dict) and isinstance(repair, dict)
    steps: list[dict] = parity.get("steps", [])  # type: ignore
    cov_items: list[dict] = spec.get("coverage", {}).get("unverified", []) if isinstance(spec.get("coverage"), dict) else []
    failing = [s for s in steps if s.get("verdict") != "pass"]
    unresolved = [f"Step {s.get('step')} s={s.get('s')} {s.get('reason', '')}" for s in failing]
    for c in cov_items:
        unresolved.append(f"Unverified: {c.get('item', '')} - {c.get('reason', '')}")
    rows = []
    for step in sorted(steps, key=lambda item: item.get("step", 0)):
        legacy = html.escape(str(step.get("legacy_frame", "")))
        current = html.escape(str(step.get("new_screenshot", "")))
        # Relative paths work both in the live report route and inside export.zip.
        legacy_url = html.escape(str(step.get("legacy_frame", "")), quote=True)
        current_url = html.escape(str(step.get("new_screenshot", "")), quote=True)
        rows.append(
            "<tr><td>{step}</td><td>{weight}</td><td>{state}</td><td>{data}</td><td>{flow}</td>"
            "<td>{visual}</td><td>{score}</td><td>{verdict}</td><td>{reason}</td>"
            "<td>{legacy}<br><a href='{legacy_url}'>open</a><br><img src='{legacy_url}' width='160'></td>"
            "<td>{current}<br><a href='{current_url}'>open</a><br><img src='{current_url}' width='160'></td></tr>".format(
                step=step.get("step"), weight=step.get("weight"), state=step.get("state"),
                data=step.get("data"), flow=step.get("flow"), visual=step.get("visual"),
                score=step.get("s"), verdict=html.escape(str(step.get("verdict", ""))),
                reason=html.escape(str(step.get("reason", ""))),
                legacy=legacy, current=current, legacy_url=legacy_url, current_url=current_url,
            )
        )
    cov_html = "".join(f"<li>{html.escape(str(c.get('item','')))} - {html.escape(str(c.get('reason','')))}</li>" for c in cov_items) or "<li>none</li>"
    rep_hist = repair.get("history", [])
    rep_html = ""
    for r in rep_hist:
        fixes = "".join(f"<li>step {f.get('step')}: {html.escape(str(f.get('cause','')))} {html.escape(str(f.get('patch','')))} "
                        f"s {f.get('s_before')} -&gt; {f.get('s_after')}</li>" for f in r.get("fixes", []))
        rep_html += f"<li>round {r.get('round')}: {r.get('parity_before')} -&gt; {r.get('parity_after')} reran_all={r.get('reran_all')}<ul>{fixes}</ul></li>"
    rep_html = rep_html or "<li>No repair history recorded.</li>"
    un_html = "".join(f"<li>{html.escape(u)}</li>" for u in unresolved) or "<li>none</li>"
    app_name = html.escape(str(spec.get("app", {}).get("name", "Rosetta")))
    out_html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Rosetta Parity Report</title>
<style>body{{font-family:system-ui;max-width:1100px;margin:20px auto}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:4px;font-size:12px}}</style>
</head><body>
<h1>Rosetta Parity Report - {app_name}</h1>
<h2>Overall score</h2><p>Parity: {parity.get('parity')} Pass: {parity.get('pass')}</p>
<h2>Per-step table</h2><table><tr><th>step</th><th>w</th><th>state</th><th>data</th><th>flow</th><th>visual</th><th>s</th><th>verdict</th><th>reason</th><th>legacy</th><th>new</th></tr>
{''.join(rows)}</table>
<h2>Coverage ledger</h2><ul>{cov_html}</ul>
<h2>Repair history</h2><ul>{rep_html}</ul><p>rounds={repair.get('rounds', 0)}</p>
<h2>Unresolved issues</h2><ul>{un_html}</ul>
</body></html>"""
    out = job_dir / "report.html"
    out.write_text(out_html, encoding="utf-8")
    log.info("wrote %s parity=%s", out, parity.get("parity"))
    return out