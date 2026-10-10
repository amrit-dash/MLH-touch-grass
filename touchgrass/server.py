"""A tiny server your phone uploads the proof photo to: on your Wi-Fi, or behind an HTTPS tunnel."""

from __future__ import annotations

import base64
import json
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Callable
from urllib.parse import parse_qs, urlparse

from touchgrass import state, verify
from touchgrass.tunnel import Tunnel

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

Verifier = Callable[[bytes, "float | None", float], verify.Verdict]


def lan_ip() -> str:
    """Best guess at the address your phone can reach this machine on."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def decode_data_url(data_url: str) -> bytes:
    _, _, encoded = data_url.partition(",")
    return base64.b64decode(encoded or data_url)


def make_handler(
    token: str,
    verifier: Verifier,
    on_pass: Callable[[verify.Verdict], None],
    on_verdict: Callable[[verify.Verdict], None] | None = None,
):
    page = resources.files("touchgrass").joinpath("page.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _authorized(self) -> bool:
            query = parse_qs(urlparse(self.path).query)
            return secrets.compare_digest(query.get("t", [""])[0], token)

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, payload: dict) -> None:
            self._send(status, json.dumps(payload).encode(), "application/json")

        def do_GET(self):
            if urlparse(self.path).path != "/" or not self._authorized():
                return self._send(404, b"not found", "text/plain")
            self._send(200, page, "text/html; charset=utf-8")

        def do_POST(self):
            if urlparse(self.path).path != "/upload" or not self._authorized():
                return self._json(404, {"error": "not found"})
            length = int(self.headers.get("Content-Length", 0))
            if length > MAX_UPLOAD_BYTES:
                return self._json(413, {"error": "Photo too large."})
            try:
                body = json.loads(self.rfile.read(length))
                jpeg = decode_data_url(body["image"])
                taken_at = body.get("taken_at")
                verdict = verifier(jpeg, float(taken_at) if taken_at else None, time.time() * 1000)
            except verify.ModelError as exc:
                return self._json(502, {"error": str(exc)})
            except (KeyError, ValueError, TypeError):
                return self._json(400, {"error": "Bad upload."})
            if on_verdict:
                on_verdict(verdict)
            try:
                self._json(200, verdict.as_dict())
            finally:
                # After responding, so the phone sees the result before we shut down,
                # but even if the phone has gone away: you still went outside.
                if verdict.passed:
                    on_pass(verdict)

    return Handler


def record_pass(verdict: verify.Verdict, indoors_minutes: float) -> None:
    state.add_receipt(
        {
            "at": state.now().isoformat(),
            "indoors_minutes": round(indoors_minutes),
            "description": verdict.description,
            "roast": verdict.roast,
        }
    )
    state.mark_grass()


def serve(
    on_ready: Callable[[str], None],
    port: int = 8765,
    verifier: Verifier = verify.verify,
    timeout_minutes: int = 30,
    tunnel: bool = False,
    public_url: str | None = None,
    on_verdict: Callable[[verify.Verdict], None] | None = None,
) -> verify.Verdict | None:
    """Serve until a photo passes or we time out. Returns the passing verdict or None.

    By default the page is on your LAN. With `tunnel`, a Cloudflare quick tunnel gives
    it an HTTPS address that works from anywhere. With `public_url`, you bring your own
    (ngrok, Tailscale Funnel, a reverse proxy) pointed at this port. Either way the server
    only listens on localhost, and the token is longer because the URL is public.
    """
    public = tunnel or public_url is not None
    token = secrets.token_urlsafe(16 if public else 8)
    passed: list[verify.Verdict] = []
    done = threading.Event()
    indoors = state.minutes_indoors()

    def on_pass(verdict: verify.Verdict) -> None:
        if not passed:
            record_pass(verdict, indoors)
            passed.append(verdict)
        done.set()

    host = "127.0.0.1" if public else "0.0.0.0"
    server = ThreadingHTTPServer((host, port), make_handler(token, verifier, on_pass, on_verdict))
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    cloudflare = Tunnel(port) if tunnel else None
    try:
        if cloudflare:
            base = cloudflare.open()
            cloudflare.wait_until_reachable(f"/?t={token}")
        elif public_url:
            base = public_url.rstrip("/")
        else:
            base = f"http://{lan_ip()}:{port}"
        on_ready(f"{base}/?t={token}")
        done.wait(timeout_minutes * 60)
    finally:
        if cloudflare:
            cloudflare.close()
        server.shutdown()
        server.server_close()
    return passed[0] if passed else None
