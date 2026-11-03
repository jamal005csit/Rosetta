"""Provider adapter for the Meta-compatible Muse API. All calls are budgeted and schema-validated."""
import base64
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from .budget import CallBudget, BudgetExceeded
from .validated_call import call_with_validation
from ..app.config import meta_base, meta_key, muse_model, max_calls_per_job

log = logging.getLogger(__name__)


class VideoNotSupported(RuntimeError):
    pass


def _endpoint_url(base: str) -> str:
    base = base.rstrip("/")
    return base if base.endswith("/chat/completions") else base + "/chat/completions"


def _headers(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _build_video_part(b64: str, mime: str = "video/mp4") -> dict:
    return {"type": "video_url", "video_url": {"url": f"data:{mime};base64,{b64}"}}


def _build_image_part(b64: str, mime: str = "image/png") -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


def _build_payload(model: str, messages: list, schema: dict, name: str = "out") -> dict:
    return {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": name, "strict": True, "schema": schema},
        },
    }


def _parse_usage(response: dict) -> tuple[int, int]:
    usage = response.get("usage", {}) or {}
    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    return prompt_tokens, completion_tokens


def _parse_content(response: dict) -> str:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"unexpected chat response shape: {exc} keys={list(response.keys())}")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("model response content is empty or not text")
    return content


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


Transport = Callable[[dict], dict]


class MuseClient:
    def __init__(
        self,
        base: str,
        key: str,
        model: str,
        job_dir: Path,
        budget: CallBudget,
        transport: Transport | None = None,
    ) -> None:
        self.base = base
        self.key = key
        self.model = model
        self.job_dir = Path(job_dir)
        self.budget = budget
        self.transport = transport
        self.job_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(
        cls,
        job_dir: Path,
        budget: CallBudget | None = None,
        transport: Transport | None = None,
    ) -> "MuseClient":
        job_dir = Path(job_dir)
        return cls(
            meta_base(),
            meta_key(),
            muse_model(),
            job_dir,
            budget or CallBudget(max_calls_per_job(), state_path=job_dir / "muse_budget.json"),
            transport,
        )

    def _log_call(
        self,
        label: str,
        elapsed_ms: int,
        prompt_tokens: int,
        completion_tokens: int,
        success: bool,
        attempt: int,
        error: str | None = None,
    ) -> None:
        record = {
            "label": label,
            "model": self.model,
            "attempt": attempt,
            "ms": elapsed_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "ok": success,
            "error": error,
        }
        log_path = self.job_dir / "muse_calls.jsonl"
        with log_path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
        log.info(
            "muse %s attempt=%d %dms prompt=%d completion=%d ok=%s",
            label, attempt, elapsed_ms, prompt_tokens, completion_tokens, success,
        )

    def _post(self, payload: dict) -> dict:
        if self.transport is not None:
            return self.transport(payload)
        if not self.key:
            raise RuntimeError("META_API_KEY missing")
        url = _endpoint_url(self.base)
        response = httpx.post(
            url, headers=_headers(self.key), json=payload, timeout=120.0
        )
        log.info("POST %s -> %d", url, response.status_code)
        if response.status_code in (400, 422) and "video" in response.text.lower():
            raise VideoNotSupported(response.text[:500])
        response.raise_for_status()
        return response.json()

    def _validated_payload(self, payload: dict, schema: dict, label: str) -> Any:
        attempt_number = 0

        def one_try(previous_error: str | None) -> tuple[Any, int, int]:
            nonlocal attempt_number
            attempt_number += 1
            try:
                self.budget.consume(label)
            except BudgetExceeded as exc:
                self._log_call(label, 0, 0, 0, False, attempt_number, str(exc))
                raise

            request_payload = dict(payload)
            if previous_error:
                request_payload["messages"] = list(payload["messages"]) + [{
                    "role": "user",
                    "content": [{
                        "type": "text",
                        "text": (
                            f"The previous response failed JSON Schema validation: {previous_error}. "
                            "Correct the response and return only valid JSON."
                        ),
                    }],
                }]

            started = time.monotonic()
            try:
                raw = self._post(request_payload)
                prompt_tokens, completion_tokens = _parse_usage(raw)
                text = _parse_content(raw)
                try:
                    data = json.loads(text)
                except json.JSONDecodeError as exc:
                    data = {"__invalid_json__": str(exc)}
                elapsed = int((time.monotonic() - started) * 1000)
                one_try.last_ms = elapsed  # type: ignore[attr-defined]
                return data, prompt_tokens, completion_tokens
            except Exception as exc:
                elapsed = int((time.monotonic() - started) * 1000)
                self._log_call(
                    label, elapsed, 0, 0, False, attempt_number,
                    f"{type(exc).__name__}: {str(exc)[:500]}",
                )
                raise

        def log_validated_attempt(
            attempt: int,
            valid: bool,
            prompt_tokens: int,
            completion_tokens: int,
            validation_error: str | None,
        ) -> None:
            elapsed = int(getattr(one_try, "last_ms", 0))
            self._log_call(
                label, elapsed, prompt_tokens, completion_tokens, valid,
                attempt, validation_error,
            )

        data, _prompt_tokens, _completion_tokens = call_with_validation(
            one_try, schema, label, on_attempt=log_validated_attempt
        )
        return data

    def chat_json(
        self,
        prompt: str,
        schema: dict,
        label: str,
        images_b64: list[str] | None = None,
    ) -> Any:
        content: list[dict] = [{"type": "text", "text": prompt}]
        for image_data in images_b64 or []:
            content.append(_build_image_part(image_data))
        payload = _build_payload(
            self.model, [{"role": "user", "content": content}], schema, label
        )
        return self._validated_payload(payload, schema, label)

    def chat_with_video(
        self,
        video_path: Path,
        prompt: str,
        schema: dict,
        label: str,
    ) -> Any:
        video_data = _build_video_part(_b64(video_path))
        content = [{"type": "text", "text": prompt}, video_data]
        payload = _build_payload(
            self.model, [{"role": "user", "content": content}], schema, label
        )
        try:
            return self._validated_payload(payload, schema, label + ":video")
        except VideoNotSupported:
            raise

    def chat_with_keyframes(
        self,
        frames: list[Path],
        transcript: str,
        prompt: str,
        schema: dict,
        label: str,
    ) -> Any:
        ordered_frames = sorted(frames)
        images = [_b64(frame) for frame in ordered_frames[:24]]
        full_prompt = prompt + "\n\nFrames in order: " + ", ".join(
            frame.name for frame in ordered_frames[:24]
        )
        if transcript.strip():
            full_prompt += "\n\nAudio transcript:\n" + transcript[:8000]
        return self.chat_json(full_prompt, schema, label, images_b64=images)
