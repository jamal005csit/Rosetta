"""Persistent per-job model-call budget shared across API stages."""
import json
import logging
import os
import threading
from pathlib import Path

log = logging.getLogger(__name__)
_LOCKS_GUARD = threading.Lock()
_LOCKS: dict[str, threading.Lock] = {}


class BudgetExceeded(RuntimeError):
    pass


class CallBudget:
    def __init__(self, max_calls: int = 50, state_path: Path | None = None) -> None:
        if max_calls < 1:
            raise ValueError("max_calls must be at least 1")
        self.max_calls = int(max_calls)
        self.state_path = Path(state_path) if state_path is not None else None
        if self.state_path is None:
            self._lock = threading.Lock()
        else:
            lock_key = str(self.state_path.resolve())
            with _LOCKS_GUARD:
                self._lock = _LOCKS.setdefault(lock_key, threading.Lock())
        self.used = self._load_used()

    def _load_used(self) -> int:
        if self.state_path is None or not self.state_path.is_file():
            return 0
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            used = int(payload.get("used", 0))
            return max(0, used)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            log.warning("could not read persisted Muse budget: %s", exc)
            raise RuntimeError("persisted Muse budget is corrupt; refusing to reset the call budget") from exc

    def _persist(self, label: str) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "used": self.used,
            "max_calls": self.max_calls,
            "last_label": label,
        }
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temporary, self.state_path)

    def consume(self, label: str = "") -> None:
        with self._lock:
            # Refresh while holding the per-job lock so API-stage clients cannot
            # spend a stale copy of the same persisted budget.
            if self.state_path is not None:
                self.used = self._load_used()
            if self.used >= self.max_calls:
                raise BudgetExceeded(
                    f"Muse call budget {self.used}/{self.max_calls} exceeded at {label}"
                )
            self.used += 1
            self._persist(label)
            log.info("Muse budget %d/%d used (%s)", self.used, self.max_calls, label)

    def remaining(self) -> int:
        with self._lock:
            if self.state_path is not None:
                self.used = self._load_used()
            return max(0, self.max_calls - self.used)
