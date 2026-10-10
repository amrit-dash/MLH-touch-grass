"""An HTTPS address for the phone page that works off your Wi-Fi.

Uses a Cloudflare quick tunnel: no account, no domain, gone when `prove` exits.
The model still runs on your laptop. The photo passes through Cloudflare
encrypted on its way to you, and nothing stores it.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request

URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
INSTALL_HINT = "Install it with `brew install cloudflared` (or see developers.cloudflare.com/cloudflared)."


class TunnelError(RuntimeError):
    pass


def find_url(line: str) -> str | None:
    match = URL_PATTERN.search(line)
    return match.group(0) if match else None


class Tunnel:
    def __init__(self, port: int, binary: str = "cloudflared"):
        self.port = port
        self.binary = binary
        self.url: str | None = None
        self.process: subprocess.Popen | None = None

    def open(self, timeout: float = 30) -> str:
        path = shutil.which(self.binary)
        if not path:
            raise TunnelError(f"`{self.binary}` isn't installed. {INSTALL_HINT}")
        self.process = subprocess.Popen(
            [path, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{self.port}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        found = threading.Event()
        log: list[str] = []

        def drain() -> None:
            # Keep reading for the tunnel's whole life so cloudflared never blocks on a full pipe.
            with self.process.stderr:
                for line in self.process.stderr:
                    log.append(line)
                    if self.url is None and (url := find_url(line)):
                        self.url = url
                        found.set()
            found.set()

        threading.Thread(target=drain, daemon=True).start()
        found.wait(timeout)
        if self.url is None:
            self.close()
            tail = "".join(log[-5:]).strip()
            raise TunnelError(f"cloudflared didn't give us an address.\n{tail}")
        return self.url

    def wait_until_reachable(self, path: str, timeout: float = 30) -> bool:
        """A new quick tunnel takes a few seconds to resolve. Don't show a QR code that 404s."""
        # Asking too early can get "no such host" cached on this machine, so give DNS a head start.
        time.sleep(3)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f"{self.url}{path}", timeout=5) as response:
                    if response.status == 200:
                        return True
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(1)
        return False

    def close(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(5)
            except subprocess.TimeoutExpired:
                self.process.kill()
