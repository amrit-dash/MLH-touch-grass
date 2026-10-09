"""Command line: install the hook, check it, prove you went outside."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

from touchgrass import state, verify
from touchgrass.server import serve

HOOK_MARKER = "# installed by touch-grass"


def _fmt(minutes: float) -> str:
    hours, mins = divmod(round(minutes), 60)
    return f"{hours}h {mins:02d}m" if hours else f"{mins}m"


def hook_script() -> str:
    python = shlex.quote(sys.executable)
    return f"#!/bin/sh\n{HOOK_MARKER}\nexec {python} -m touchgrass check\n"


def git_hooks_dir() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--git-path", "hooks"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return Path(out).resolve()


def cmd_install(args) -> int:
    try:
        hooks = git_hooks_dir()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Not inside a git repository.", file=sys.stderr)
        return 1
    hooks.mkdir(parents=True, exist_ok=True)
    hook = hooks / "pre-push"
    if hook.exists() and HOOK_MARKER not in hook.read_text() and not args.force:
        print(f"{hook} already exists. Re-run with --force to replace it.", file=sys.stderr)
        return 1
    hook.write_text(hook_script())
    hook.chmod(0o755)
    state.ensure_baseline()
    print(f"🌱 Installed. Pushes from this repo now need grass every {_fmt(state.max_minutes())}.")
    return 0


def cmd_check(args) -> int:
    state.ensure_baseline()
    indoors = state.minutes_indoors()
    limit = state.max_minutes()
    if indoors <= limit:
        return 0
    print(
        f"\n🌱 touch-grass: {_fmt(indoors)} since you last saw the sky. Push blocked.\n"
        "   Run `touchgrass prove`, scan the code with your phone and take a photo outside.\n"
        "   (Yes, `git push --no-verify` works. You'll know.)\n",
        file=sys.stderr,
    )
    return 1


def _print_qr(url: str) -> None:
    try:
        import qrcode
    except ImportError:
        return
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.print_ascii(invert=True)


def cmd_prove(args) -> int:
    def on_ready(url: str) -> None:
        _print_qr(url)
        print(f"📱 On your phone (same Wi-Fi), open:\n   {url}")
        print(f"   Model: {verify.model_name()} via {verify.ollama_host()}")
        print("   Waiting for a photo of the outside world… (Ctrl+C to give up)")

    try:
        verdict = serve(on_ready, port=args.port, timeout_minutes=args.timeout)
    except KeyboardInterrupt:
        print("\nStill indoors, then.")
        return 1
    if verdict is None:
        print("Timed out. The grass will wait.")
        return 1
    print(f"\n✅ {verdict.reason} {verdict.description}")
    if verdict.roast:
        print(f"   “{verdict.roast}”")
    print("   Push unlocked.")
    return 0


def cmd_status(args) -> int:
    state.ensure_baseline()
    indoors = state.minutes_indoors()
    limit = state.max_minutes()
    left = limit - indoors
    if left > 0:
        print(f"🌱 {_fmt(indoors)} indoors. {_fmt(left)} until your pushes need grass.")
    else:
        print(f"🚫 {_fmt(indoors)} indoors. Pushes blocked. Run `touchgrass prove`.")
    return 0


def cmd_log(args) -> int:
    receipts = state.receipts()
    if not receipts:
        print("No grass receipts yet.")
        return 0
    for r in receipts[-args.n:]:
        print(f"{r['at'][:16].replace('T', ' ')}  after {_fmt(r.get('indoors_minutes') or 0)} indoors")
        if r.get("description"):
            print(f"   {r['description']}")
        if r.get("roast"):
            print(f"   “{r['roast']}”")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="touchgrass", description="Go outside before you push.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("install", help="install the pre-push hook in this git repo")
    p.add_argument("--force", action="store_true", help="replace an existing pre-push hook")
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("check", help="exit 1 if you've been inside too long (used by the hook)")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("prove", help="serve the phone page and wait for an outdoor photo")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--timeout", type=int, default=30, help="minutes to wait")
    p.set_defaults(func=cmd_prove)

    p = sub.add_parser("status", help="how long you've been indoors")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("log", help="show your grass receipts")
    p.add_argument("-n", type=int, default=10)
    p.set_defaults(func=cmd_log)

    args = parser.parse_args(argv)
    return args.func(args)
