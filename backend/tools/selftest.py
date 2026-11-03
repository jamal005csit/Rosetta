"""AT-01: schema-valid JSON from sample recording via MuseClient path."""
import argparse
import base64
import json
import logging
import tempfile
from pathlib import Path

from backend.muse.client import MuseClient
from backend.muse.budget import CallBudget

log = logging.getLogger(__name__)
PNG1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

def schema() -> dict:
    p = Path(__file__).resolve().parents[1] / "schemas" / "observations.schema.json"
    return json.loads(p.read_text(encoding="utf-8"))

def fake_transport_factory(first_invalid: bool = True):
    calls = {"n": 0}
    valid = {"observations": [{"t": 1.2, "action": "type", "target_label": "Username",
             "typed_text": "admin", "screen_after": {"title": "Login"}}]}
    invalid = {"bad": 1}
    def tr(payload: dict) -> dict:
        calls["n"] += 1
        data = invalid if (first_invalid and calls["n"] == 1) else valid
        return {"choices": [{"message": {"content": json.dumps(data)}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
    tr.calls = calls  # type: ignore
    return tr

def run(mock: bool = True) -> dict:
    with tempfile.TemporaryDirectory() as td:
        jd = Path(td)
        (jd / "frames").mkdir()
        for i in range(2):
            (jd / "frames" / f"frame_{i:04d}.png").write_bytes(PNG1)
        tr = fake_transport_factory(True)
        client = MuseClient("https://api.meta.ai/v1", "test", "muse-spark-1.3",
                            jd, CallBudget(10), transport=tr)
        prompt = (Path(__file__).resolve().parents[1] / "prompts" / "observer.md").read_text()
        data = client.chat_with_keyframes(list((jd / "frames").glob("*.png")), "hello",
                                          prompt, schema(), "observer")
        assert (jd / "muse_calls.jsonl").exists(), "P5 log missing"
        log.info("selftest ok calls=%s", tr.calls)  # type: ignore
        return data

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", default=True)
    ap.add_argument("--live", action="store_true", default=False)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    if a.live:
        raise SystemExit("live selftest needs META_API_KEY; run with --mock in CI")
    print(json.dumps(run(True), indent=2))

if __name__ == "__main__":
    main()