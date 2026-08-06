"""Robust JSON extraction from LLM text output."""
import json
import re

_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_BARE_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(text: str) -> dict:
    """Parses a JSON object out of LLM output, tolerating markdown code fences and
    leading/trailing prose the model added despite being told not to.

    Raises json.JSONDecodeError (a ValueError subclass) if no valid object is found.
    """
    text = text.strip()

    fence_match = _FENCED_JSON_RE.search(text)
    if fence_match:
        text = fence_match.group(1)
    else:
        brace_match = _BARE_JSON_RE.search(text)
        if brace_match:
            text = brace_match.group(0)

    return json.loads(text)
