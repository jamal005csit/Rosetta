"""ONLY file that talks to Meta Model API. P5 + P6.

ADJUST MAP if your Meta endpoint differs from OpenAI-compatible assumption:
  ADJUST-1 (_endpoint_url): URL path. Assumed {BASE}/chat/completions
  ADJUST-2 (_headers): auth scheme. Assumed Bearer META_API_KEY
  ADJUST-3 (_build_video_part): video attach shape. Assumed {"type":"video_url",...}
  ADJUST-4 (_build_image_part): image attach shape. Assumed {"type":"image_url",...}
  ADJUST-5 (_build_payload): response_format json_schema shape
  ADJUST-6 (_parse_usage): usage field names
  ADJUST-7 (_parse_content): message content extraction
All other logic (retries/validation/budget/logging) is provider-agnostic.
"""
import base64
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from .budget import CallBudget, BudgetExceeded
from .validated_call import call_with_validation
from ..app.config import meta_base, meta_key, muse_model

log = logging.getLogger(__name__)

class VideoNotSupported(RuntimeError):
    pass

# ---- ADJUST-1 ----
def _endpoint_url(base: str) -> str:
    base = base.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"

# ---- ADJUST-2 ----
def _headers(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

# ---- ADJUST-3 ----
def _build_video_part(b64: str, mime: str = "video/mp4") -> dict:
    # If Meta rejects this, change to vendor shape, e.g. {"type":"input_video",...}
    return {"type": "video_url", "video_url": {"url": f"data:{mime};base64,{b64}"}}

# ---- ADJUST-4 ----
def _build_image_part(b64: str, mime: str = "image/png") -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}

# ---- ADJUST-5 ----
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

# ---- ADJUST-6 ----
def _parse_usage(resp: dict) -> tuple[int, int]:
    u = resp.get("usage", {}) or {}
    pt = int(u.get("prompt_tokens", 0) or 0)
    ct = int(u.get("completion_tokens", 0) or 0)
    return pt, ct

# ---- ADJUST-7 ----
def _parse_content(resp: dict) -> str:
    try:
        return resp["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"unexpected chat response shape: {e} keys={list(resp.keys())}")

def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")

Transport = Callable[[dict], dict]  # payload -> raw response json (for tests)

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
        self.job_dir = job_dir
        self.budget = budget
        self.transport = transport
        self.job_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls, job_dir: Path, budget: CallBudget | None = None,
                 transport: Transport | None = None) -> "MuseClient":
        from ..app.config import max_calls_per_job
        return cls(meta_base(), meta_key(), muse_model(), job_dir,
                   budget or CallBudget(max_calls_per_job()), transport)

    def _log_call(self, label: str, ms: int, pt: int, ct: int, ok: bool) -> None:
        line = {"label": label, "model": self.model, "ms": ms,
                "prompt_tokens": pt, "completion_tokens": ct, "ok": ok}
        lp = self.job_dir / "muse_calls.jsonl"
        with lp.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
        log.info("muse %s %dms pt=%d ct=%d ok=%s", label, ms, pt, ct, ok)

    def _post(self, payload: dict) -> dict:
        if self.transport is not None:
            return self.transport(payload)
        if not self.key:
            raise RuntimeError("META_API_KEY missing")
        url = _endpoint_url(self.base)
        t0 = time.time()
        r = httpx.post(url, headers=_headers(self.key), json=payload, timeout=120.0)
        ms = int((time.time() - t0) * 1000)
        log.info("POST %s -> %d in %dms", url, r.status_code, ms)
        if r.status_code in (400, 422) and "video" in r.text.lower():
            raise VideoNotSupported(r.text[:500])
        r.raise_for_status()
        return r.json()

    def chat_json(self, prompt: str, schema: dict, label: str,
                  images_b64: list[str] | None = None) -> Any:
        self.budget.consume(label)
        content: list[dict] = [{"type": "text", "text": prompt}]
        for b in images_b64 or []:
            content.append(_build_image_part(b))
        messages = [{"role": "user", "content": content}]
        payload = _build_payload(self.model, messages, schema, label)

        def one_try(prev_err: str | None) -> tuple[Any, int, int]:
            p = dict(payload)
            if prev_err:
                p["messages"] = [{"role": "user", "content": content},
                                 {"role": "user", "content": [
                                     {"type": "text",
                                      "text": f"Prior output failed validation: {prev_err}. Return ONLY valid JSON."}]}]
            t0 = time.time()
            raw = self._post(p)
            ms = int((time.time() - t0) * 1000)
            pt, ct = _parse_usage(raw)
            txt = _parse_content(raw)
            try:
                data = json.loads(txt)
            except json.JSONDecodeError as e:
                self._log_call(label, ms, pt, ct, False)
                return {"__invalid_json__": str(e)}, pt, ct
            self._log_call(label, ms, pt, ct, True)
            # stash last usage for outer log accuracy
            one_try.last = (ms, pt, ct)  # type: ignore
            return data, pt, ct

        data, _, _ = call_with_validation(one_try, schema, label)
        return data

    def chat_with_video(self, video_path: Path, prompt: str, schema: dict, label: str) -> Any:
        self.budget.consume(label + ":video")
        b64 = _b64(video_path)
        content = [{"type": "text", "text": prompt}, _build_video_part(b64)]
        payload = _build_payload(self.model, [{"role": "user", "content": content}], schema, label)
        t0 = time.time()
        try:
            raw = self._post(payload)
        except VideoNotSupported:
            raise
        ms = int((time.time() - t0) * 1000)
        pt, ct = _parse_usage(raw)
        self._log_call(label + ":video", ms, pt, ct, True)
        return json.loads(_parse_content(raw))

    def chat_with_keyframes(self, frames: list[Path], transcript: str,
                            prompt: str, schema: dict, label: str) -> Any:
        ordered = sorted(frames)
        imgs = [_b64(p) for p in ordered[:24]]
        full = prompt + "\n\nFrames in order: " + ", ".join(p.name for p in ordered[:24])
        if transcript.strip():
            full += "\n\nAudio transcript:\n" + transcript[:8000]
        return self.chat_json(full, schema, label, images_b64=imgs)