"""Per-job call budget. P5."""
import logging

log = logging.getLogger(__name__)

class BudgetExceeded(RuntimeError):
    pass

class CallBudget:
    def __init__(self, max_calls: int = 50) -> None:
        self.max_calls = max_calls
        self.used = 0

    def consume(self, label: str = "") -> None:
        if self.used >= self.max_calls:
            raise BudgetExceeded(f"budget {self.used}/{self.max_calls} exceeded at {label}")
        self.used += 1
        log.info("budget %d/%d used (%s)", self.used, self.max_calls, label)

    def remaining(self) -> int:
        return self.max_calls - self.used