"""JSON-schema validation with at most two budgeted correction attempts."""
import logging
from typing import Any, Callable

import jsonschema

log = logging.getLogger(__name__)
MAX_RETRIES = 2
AttemptLogger = Callable[[int, bool, int, int, str | None], None]


def validate_json(instance: Any, schema: dict) -> str | None:
    try:
        jsonschema.validate(instance=instance, schema=schema)
        return None
    except jsonschema.ValidationError as exc:
        message = f"{exc.message} at {'/'.join(str(part) for part in exc.path)}"
        log.warning("schema validation failed: %s", message)
        return message


def call_with_validation(
    fn: Callable[[str | None], tuple[Any, int, int]],
    schema: dict,
    label: str = "",
    on_attempt: AttemptLogger | None = None,
) -> tuple[Any, int, int]:
    """Call fn(error) and validate its result, retrying invalid output at most twice.

    The callback runs after validation, so success is never logged before a schema
    has actually passed. Each invocation of fn is a separately budgeted API attempt.
    """
    previous_error: str | None = None
    for attempt in range(1, MAX_RETRIES + 2):
        data, prompt_tokens, completion_tokens = fn(previous_error)
        error = validate_json(data, schema)
        valid = error is None
        if on_attempt is not None:
            on_attempt(attempt, valid, prompt_tokens, completion_tokens, error)
        if valid:
            log.info("%s schema valid on attempt %d", label, attempt)
            return data, prompt_tokens, completion_tokens
        previous_error = error
        log.warning("%s attempt %d failed schema validation: %s", label, attempt, error)
    raise ValueError(
        f"{label} failed schema validation after {MAX_RETRIES + 1} attempts: {previous_error}"
    )
