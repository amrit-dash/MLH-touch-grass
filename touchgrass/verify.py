"""Ask a local open-weight vision model whether a photo was really taken outside.

Everything runs on your machine through Ollama: the photo never leaves it.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_MODEL = "gemma4:e4b"
DEFAULT_HOST = "http://localhost:11434"
MAX_PHOTO_AGE_SECONDS = 15 * 60

PROMPT = """You are the bouncer for a developer who is not allowed to push code until they go outside.
Look at this photo and answer ONLY with a JSON object with these keys:
- "outdoors": true if the photo was clearly taken outside (open air, not through a window)
- "sky_or_plants": true if sky, grass, trees or other plants are visible
- "photo_of_screen": true if this is a photo of a monitor, phone, TV or printed picture rather than a real scene
- "description": one short sentence describing what is in the photo
- "roast": one short, friendly, funny sentence for the developer about their outing (or their attempt to cheat)
"""


class ModelError(RuntimeError):
    pass


@dataclass
class Verdict:
    passed: bool
    reason: str
    description: str = ""
    roast: str = ""

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "reason": self.reason,
            "description": self.description,
            "roast": self.roast,
        }


def model_name() -> str:
    return os.environ.get("TOUCHGRASS_MODEL", DEFAULT_MODEL)


def ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", DEFAULT_HOST).rstrip("/")


def check_freshness(taken_at_ms: float | None, now_ms: float) -> str | None:
    """Return a rejection reason if the photo is old or from the future, else None."""
    if taken_at_ms is None:
        return "No capture time on the photo. Use the camera button, not the gallery."
    age = (now_ms - taken_at_ms) / 1000
    if age > MAX_PHOTO_AGE_SECONDS:
        return f"That photo is {int(age // 60)} minutes old. Go back out and take a fresh one."
    if age < -60:
        return "That photo was taken in the future. Impressive, but no."
    return None


def ask_model(jpeg: bytes, timeout: float = 120) -> dict:
    body = json.dumps(
        {
            "model": model_name(),
            "prompt": PROMPT,
            "images": [base64.b64encode(jpeg).decode()],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.2},
        }
    ).encode()
    request = urllib.request.Request(
        f"{ollama_host()}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read())
    except urllib.error.URLError as exc:
        raise ModelError(
            f"Couldn't reach Ollama at {ollama_host()} ({exc.reason}). "
            f"Is it running? Try `ollama pull {model_name()}`."
        ) from exc
    return parse_model_output(payload.get("response", ""))


def parse_model_output(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ModelError(f"Model didn't return JSON: {text[:200]!r}")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ModelError(f"Model returned malformed JSON: {text[:200]!r}") from exc


def _truthy(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value)


def judge(answer: dict) -> Verdict:
    description = str(answer.get("description", ""))
    roast = str(answer.get("roast", ""))
    if _truthy(answer.get("photo_of_screen")):
        reason = "That's a picture of a screen. Nice try."
    elif not _truthy(answer.get("outdoors")):
        reason = "That doesn't look like outside."
    elif not _truthy(answer.get("sky_or_plants")):
        reason = "Outside, sure, but no sky or plants in sight. Find some nature."
    else:
        return Verdict(True, "Grass confirmed.", description, roast)
    return Verdict(False, reason, description, roast)


def verify(jpeg: bytes, taken_at_ms: float | None, now_ms: float) -> Verdict:
    stale = check_freshness(taken_at_ms, now_ms)
    if stale:
        return Verdict(False, stale)
    return judge(ask_model(jpeg))
