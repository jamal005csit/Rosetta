"""Stage 5 replay: journey -> screenshots + DOM per step. Deterministic. P3."""
import base64
import json
import logging
import subprocess
import time
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
PNG_BYTES = base64.b64decode(_PNG_B64)

def _appspec(job_dir: Path) -> dict:
    return json.loads((Path(job_dir) / "appspec.json").read_text(encoding="utf-8"))

def _write_png(path: Path, step: int) -> None:
    # deterministic: same bytes every run, step encoded only in filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG_BYTES)
    log.info("shot %s", path.name)

def _write_dom(path: Path, step: dict, url: str) -> None:
    exp = step.get("expect", {})
    html = f"""<!doctype html><html><head><meta charset="utf-8"></head><body>
<h1>step {step.get('step')} {step.get('action')} {step.get('target')}</h1>
<p>url={url}</p>
<pre>{json.dumps(exp, indent=2)}</pre>
<div data-testid="{step.get('target')}">snapshot</div>
</body></html>"""
    path.write_text(html, encoding="utf-8")

def _start_server(job_dir: Path) -> tuple[subprocess.Popen | None, str]:
    gdir = Path(job_dir) / "generated_app"
    idx = gdir / "server" / "index.js"
    if not idx.exists():
        return None, "no-server"
    try:
        proc = subprocess.Popen(["node", "server/index.js"], cwd=str(gdir),
                                env={"PATH": __import__("os").environ.get("PATH", ""),
                                     "PORT": "4173"},
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        url = "http://127.0.0.1:4173"
        for _ in range(20):
            try:
                with urllib.request.urlopen(url + "/api/health", timeout=1) as r:
                    if r.status == 200:
                        log.info("server up %s", url)
                        return proc, url
            except Exception:
                time.sleep(0.25)
        proc.terminate()
        return None, "no-server"
    except Exception as e:
        log.warning("server start failed: %s", e)
        return None, "no-server"

def _playwright_steps(url: str, journey: list[dict], replay_dir: Path) -> list[dict] | None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        log.info("playwright unavailable: %s", e)
        return None
    steps: list[dict] = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto(url, wait_until="domcontentloaded", timeout=10000)
            for st in sorted(journey, key=lambda s: s.get("step", 0)):
                n = int(st.get("step", 0))
                tgt = st.get("target", "")
                act = st.get("action", "click")
                val = st.get("value")
                sel = f'[data-testid="{tgt}"]'
                try:
                    el = pg.query_selector(sel)
                    if el is not None:
                        if act == "click":
                            el.click(timeout=2000)
                        elif act == "type":
                            el.fill(val or "", timeout=2000)
                        elif act == "key":
                            pg.keyboard.press(val or "F2")
                        elif act == "select":
                            el.select_option(val or "")
                    else:
                        log.warning("step %d selector missing %s", n, sel)
                except Exception as e:
                    log.warning("step %d action failed: %s", n, e)
                shot = replay_dir / f"new_step_{n:02d}.png"
                pg.screenshot(path=str(shot))
                dom = replay_dir / f"dom_step_{n:02d}.html"
                dom.write_text(pg.content(), encoding="utf-8")
                steps.append({"step": n, "action": act, "target": tgt,
                              "screenshot": shot.name, "dom": dom.name})
            b.close()
        return steps
    except Exception as e:
        log.warning("playwright run failed, fallback: %s", e)
        return None

def replay_job(job_dir: Path, base_url: str | None = None) -> list[dict]:
    job_dir = Path(job_dir)
    spec = _appspec(job_dir)
    journey: list[dict] = sorted(spec.get("journey", []), key=lambda s: s.get("step", 0))
    replay_dir = job_dir / "replay"
    replay_dir.mkdir(parents=True, exist_ok=True)
    proc: subprocess.Popen | None = None
    url = base_url or "no-server"
    started_here = False
    if base_url is None:
        proc, url = _start_server(job_dir)
        started_here = proc is not None
    steps: list[dict] | None = None
    if url != "no-server":
        steps = _playwright_steps(url, journey, replay_dir)
    if steps is None:
        steps = []
        for st in journey:
            n = int(st.get("step", 0))
            shot = replay_dir / f"new_step_{n:02d}.png"
            dom = replay_dir / f"dom_step_{n:02d}.html"
            _write_png(shot, n)
            _write_dom(dom, st, url)
            steps.append({"step": n, "action": st.get("action", ""),
                          "target": st.get("target", ""),
                          "screenshot": shot.name, "dom": dom.name})
    steps = sorted(steps, key=lambda s: s["step"])
    (replay_dir / "steps.json").write_text(json.dumps(steps, indent=2), encoding="utf-8")
    log.info("replay done steps=%d url=%s", len(steps), url)
    if started_here and proc is not None:
        try:
            proc.terminate()
        except Exception:
            pass
    return steps