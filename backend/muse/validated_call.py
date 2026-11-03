"""JSON-schema validation + <=2 retries. P5."""
import logging
from typing import Any, Callable
import jsonschema

log = logging.getLogger(__name__)
MAX_RETRIES = 2

def validate_json(instance: Any, schema: dict) -> str | None:
    try:
        jsonschema.validate(instance=instance, schema=schema)
        return None
    except jsonschema.ValidationError as e:
        msg = f"{e.message} at {'/'.join(str(x) for x in e.path)}"
        log.warning("validation failed: %s", msg)
        return msg

def call_with_validation(
    fn: Callable[[str | None], tuple[Any, int, int]],
    schema: dict,
    label: str = "",
) -> tuple[Any, int, int]:
    """fn(validation_error) -> (parsed_json, prompt_tokens, completion_tokens).
    Retries at most 2 times, each retry includes prior error. Returns parsed."""
    last_err: str | None = None
    for attempt in range(1 + MAX_RETRIES):
        data, pt, ct = fn(last_err)
        err = validate_json(data, schema)
        if err is None:
            log.info("%s valid on attempt %d", label, attempt + 1)
            return data, pt, ct
        last_err = err
        log.warning("%s attempt %d invalid: %s", label, attempt + 1, err)
    raise ValueError(f"{label} failed validation after {1 + MAX_RETRIES} attempts: {last_err}")