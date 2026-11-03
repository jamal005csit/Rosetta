import json
from pathlib import Path
import tempfile

import pytest

from backend.muse.budget import BudgetExceeded, CallBudget
from backend.muse.client import MuseClient


def _response(data: dict) -> dict:
    return {
        "choices": [{"message": {"content": json.dumps(data)}}],
        "usage": {"prompt_tokens": 7, "completion_tokens": 3},
    }


def test_budget_persists_across_client_instances_and_counts_retries():
    with tempfile.TemporaryDirectory() as td:
        job_dir = Path(td)
        state_path = job_dir / "muse_budget.json"
        first = CallBudget(3, state_path=state_path)
        first.consume("initial")
        second = CallBudget(3, state_path=state_path)
        assert second.used == 1
        assert second.remaining() == 2
        second.consume("second")
        second.consume("third")
        with pytest.raises(BudgetExceeded):
            second.consume("fourth")


def test_schema_retry_consumes_budget_and_logs_only_validated_success():
    with tempfile.TemporaryDirectory() as td:
        job_dir = Path(td)
        calls = {"count": 0}

        def transport(_payload):
            calls["count"] += 1
            if calls["count"] == 1:
                return _response({"unexpected": True})
            return _response({"ok": True})

        budget = CallBudget(5, state_path=job_dir / "muse_budget.json")
        client = MuseClient("https://example.invalid/v1", "key", "test-model", job_dir, budget, transport)
        result = client.chat_json("test", {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}, "test")

        assert result == {"ok": True}
        assert budget.used == 2
        rows = [json.loads(line) for line in (job_dir / "muse_calls.jsonl").read_text(encoding="utf-8").splitlines()]
        assert [row["ok"] for row in rows] == [False, True]
        assert [row["attempt"] for row in rows] == [1, 2]
        assert rows[1]["prompt_tokens"] == 7


def test_video_calls_are_schema_validated_and_budgeted():
    with tempfile.TemporaryDirectory() as td:
        job_dir = Path(td)
        video = job_dir / "clip.mp4"
        video.write_bytes(b"video bytes")
        budget = CallBudget(3, state_path=job_dir / "muse_budget.json")
        client = MuseClient(
            "https://example.invalid/v1", "key", "test-model", job_dir, budget,
            lambda _payload: _response({"ok": True}),
        )
        result = client.chat_with_video(
            video, "describe", {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}, "video-test"
        )
        assert result == {"ok": True}
        assert budget.used == 1
        row = json.loads((job_dir / "muse_calls.jsonl").read_text(encoding="utf-8").splitlines()[0])
        assert row["ok"] is True
        assert row["label"] == "video-test:video"


def test_transport_failure_is_logged_as_failure():
    with tempfile.TemporaryDirectory() as td:
        job_dir = Path(td)

        def broken(_payload):
            raise RuntimeError("offline")

        client = MuseClient("https://example.invalid/v1", "key", "test-model", job_dir, CallBudget(2), broken)
        with pytest.raises(RuntimeError, match="offline"):
            client.chat_json("test", {"type": "object"}, "network-test")
        row = json.loads((job_dir / "muse_calls.jsonl").read_text(encoding="utf-8").splitlines()[0])
        assert row["ok"] is False
        assert "offline" in row["error"]
