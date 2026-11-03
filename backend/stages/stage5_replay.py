"""Stage 5: execute the journey in a real browser and persist observed evidence."""
import json
import logging
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)


def _appspec(job_dir: Path) -> dict:
    return json.loads((Path(job_dir) / "appspec.json").read_text(encoding="utf-8"))


def _npm_command(*args: str) -> list[str]:
    if os.name == "nt":
        return ["cmd", "/c", "npm", *args]
    return ["npm", *args]


def _install_dependencies(generated_dir: Path) -> None:
    if not shutil.which("npm") and os.name != "nt":
        raise RuntimeError("npm is required for replay; install Node.js and npm")
    result = subprocess.run(
        _npm_command("install", "--no-audit", "--no-fund"),
        cwd=str(generated_dir), capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "npm install failed; replay cannot use fabricated evidence. "
            + result.stderr[-2000:]
        )


def _start_server(job_dir: Path) -> tuple[subprocess.Popen, str]:
    generated_dir = Path(job_dir) / "generated_app"
    package_file = generated_dir / "package.json"
    if not package_file.is_file():
        raise FileNotFoundError("generated_app/package.json is missing; run generate first")
    if not (generated_dir / "node_modules").is_dir():
        _install_dependencies(generated_dir)

    env = os.environ.copy()
    env["PORT"] = "4173"
    command = _npm_command("start")
    process = subprocess.Popen(
        command, cwd=str(generated_dir), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = "http://127.0.0.1:4173"
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError("generated app exited before becoming healthy")
        try:
            with urllib.request.urlopen(url + "/api/health", timeout=1) as response:
                if response.status == 200:
                    log.info("generated app healthy at %s", url)
                    return process, url
        except Exception:
            time.sleep(0.5)
    process.terminate()
    raise RuntimeError("generated app did not become healthy within 60 seconds")


def _snapshot_page(page) -> dict:
    return page.evaluate("""() => {
      const root = document.querySelector('[data-testid="active-screen"]') || document.body;
      const fields = {};
      root.querySelectorAll('[data-testid]').forEach((element) => {
        const id = element.getAttribute('data-testid');
        const value = ('value' in element) ? element.value : (element.innerText || '').trim();
        fields[id] = value;
      });
      return {
        active_screen: root.getAttribute('data-screen-id'),
        text: root.innerText || '',
        fields,
        title: document.title,
        url: window.location.href
      };
    }""")


def _playwright_steps(url: str, journey: list[dict], replay_dir: Path) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError(
            "Playwright is required for genuine replay. Install dependencies and run "
            "'python -m playwright install chromium'."
        ) from exc

    steps: list[dict] = []
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Exception as exc:
            raise RuntimeError(
                "Chromium is not installed for Playwright. Run "
                "'python -m playwright install chromium'."
            ) from exc
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(url, wait_until="networkidle", timeout=30000)
            for journey_step in sorted(journey, key=lambda row: int(row["step"])):
                number = int(journey_step["step"])
                action = journey_step["action"]
                target = journey_step["target"]
                value = journey_step.get("value")
                success = False
                error = None
                target_found = action == "key"
                try:
                    if action == "key":
                        page.keyboard.press(str(value or "F2"))
                    else:
                        locator = page.get_by_test_id(str(target))
                        target_found = locator.count() > 0
                        if not target_found:
                            raise RuntimeError(f"target data-testid not found: {target}")
                        if action == "click":
                            locator.click(timeout=5000)
                        elif action == "type":
                            locator.fill("" if value is None else str(value), timeout=5000)
                        elif action == "select":
                            locator.select_option("" if value is None else str(value), timeout=5000)
                        else:
                            raise ValueError(f"unsupported replay action: {action}")
                    success = True
                except Exception as exc:
                    error = str(exc)[:1000]
                    log.warning("replay step %d failed: %s", number, error)

                page.wait_for_timeout(100)
                screenshot = replay_dir / f"new_step_{number:02d}.png"
                dom_file = replay_dir / f"dom_step_{number:02d}.html"
                snapshot_file = replay_dir / f"snapshot_step_{number:02d}.json"
                page.screenshot(path=str(screenshot), full_page=True)
                dom_file.write_text(page.content(), encoding="utf-8")
                snapshot = _snapshot_page(page)
                snapshot_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
                steps.append({
                    "step": number,
                    "action": action,
                    "target": target,
                    "success": success,
                    "target_found": target_found,
                    "error": error,
                    "active_screen": snapshot.get("active_screen"),
                    "screenshot": screenshot.name,
                    "dom": dom_file.name,
                    "snapshot": snapshot_file.name,
                    "url": snapshot.get("url"),
                })
        finally:
            browser.close()
    return steps


def replay_job(job_dir: Path, base_url: str | None = None) -> list[dict]:
    job_dir = Path(job_dir)
    spec = _appspec(job_dir)
    journey = sorted(spec.get("journey", []), key=lambda row: int(row["step"]))
    if not journey:
        raise ValueError("AppSpec journey is empty; replay cannot proceed")

    # Verify legacy evidence before launching anything. Never synthesize a missing frame.
    for journey_step in journey:
        frame = Path(journey_step["legacy_frame"])
        if frame.is_absolute() or ".." in frame.parts or not (job_dir / frame).is_file():
            raise FileNotFoundError(f"legacy evidence frame is missing or unsafe: {journey_step['legacy_frame']}")

    replay_dir = job_dir / "replay"
    replay_dir.mkdir(parents=True, exist_ok=True)
    for pattern in ("new_step_*.png", "dom_step_*.html", "snapshot_step_*.json", "steps.json"):
        for stale in replay_dir.glob(pattern):
            stale.unlink()

    process = None
    try:
        if base_url is None:
            process, url = _start_server(job_dir)
        else:
            url = base_url
        steps = _playwright_steps(url, journey, replay_dir)
        if len(steps) != len(journey):
            raise RuntimeError("Playwright did not produce one result per journey step")
        output = replay_dir / "steps.json"
        output.write_text(json.dumps(steps, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info(
            "replay completed steps=%d successful=%d",
            len(steps), sum(1 for step in steps if step["success"])
        )
        return steps
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
