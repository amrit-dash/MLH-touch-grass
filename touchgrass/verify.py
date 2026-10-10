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
Developers cheat by photographing a screen or a printed picture of nature, so check that first.

Answer ONLY with a JSON object with these keys, in this order:
- "screen_evidence": what you see that suggests a display, monitor, TV, phone, laptop or printed picture
  (bezels, a frame around the scene, a stand, a keyboard, desk edges, glare, pixels, moire), or "none"
- "photo_of_screen": true if the main scene is shown on a screen or a print, even if that scene is outdoors
- "outdoors": true if the photographer was standing outside in the open air (not behind a window)
- "sky_or_plants": true if real sky, grass, trees or other plants are visible
- "description": one short sentence describing what is in the photo
- "roast": one short, friendly, funny sentence for the developer that mentions something specific in
  this photo. Don't start with "Looks like".
"""

# A second, narrower question for photos that passed. Small models miss a bezel when
# the screen fills the frame, but catch it when that's the only thing they're asked.
SCREEN_PROMPT = """Look closely at the edges and borders of this photo.
Is the scene being displayed on a monitor, TV, laptop, tablet, phone or printed picture that someone photographed?
Signs: a plastic or metal bezel or frame running along the edges, a power light or logo on a frame, a stand,
screen glare, visible pixels or moire, a sharp rectangular border around the scene.
Answer ONLY with JSON: {"border_seen": "<what is at the edges of the photo>", "on_screen": true or false}
"""


SCREEN_REASON = "That's a picture of a screen. Nice try."


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


def ask_model(jpeg: bytes, prompt: str = PROMPT, temperature: float = 0.2, timeout: float = 300) -> dict:
    body = {
        "model": model_name(),
        "prompt": prompt,
        "images": [base64.b64encode(jpeg).decode()],
        "format": "json",
        "think": False,
        "stream": False,
        "options": {"temperature": temperature},
    }
    try:
        payload = _generate(body, timeout)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        if "structured output" not in detail:
            raise ModelError(f"Ollama returned {exc.code}: {detail[:200]}") from exc
        # Some Ollama builds (e.g. Homebrew's MLX runner) can't do format=json.
        # The prompt already asks for JSON and parse_model_output digs it out.
        del body["format"]
        payload = _generate(body, timeout)
    return parse_model_output(payload.get("response", ""))


def _generate(body: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        f"{ollama_host()}/api/generate",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError:
        raise
    except urllib.error.URLError as exc:
        raise ModelError(
            f"Couldn't reach Ollama at {ollama_host()} ({exc.reason}). "
            f"Is it running? Try `ollama pull {model_name()}`."
        ) from exc


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
        reason = SCREEN_REASON
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
    return check(jpeg)


def check(jpeg: bytes, timeout: float = 300) -> Verdict:
    """The model part of verify(): describe the photo, then double-check passes for a screen."""
    verdict = judge(ask_model(jpeg, timeout=timeout))
    if verdict.passed and on_screen(jpeg, timeout):
        verdict.passed = False
        verdict.reason = SCREEN_REASON
    return verdict


def on_screen(jpeg: bytes, timeout: float = 300) -> bool:
    answer = ask_model(jpeg, SCREEN_PROMPT, temperature=0, timeout=timeout)
    return _truthy(answer.get("on_screen"))
