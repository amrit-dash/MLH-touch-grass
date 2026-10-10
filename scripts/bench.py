"""Benchmark the bouncer: run the real model over labelled photos.

    python scripts/bench.py PHOTOS_DIR [--out results.json]

PHOTOS_DIR must contain `pass/` (should unlock) and `fail/` (should stay locked).
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from touchgrass import verify  # noqa: E402


def as_jpeg(path: Path) -> bytes:
    """Match what the phone page sends: JPEG, longest side <= 1024."""
    try:
        from PIL import Image
    except ImportError:
        return path.read_bytes()
    im = Image.open(path).convert("RGB")
    im.thumbnail((1024, 1024))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("photos", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    rows = []
    for expected in ("pass", "fail"):
        for path in sorted((args.photos / expected).glob("*.jp*g")):
            start = time.monotonic()
            try:
                verdict = verify.check(as_jpeg(path), timeout=900)
            except verify.ModelError as exc:
                verdict = verify.Verdict(False, f"error: {exc}")
            seconds = time.monotonic() - start
            ok = verdict.passed == (expected == "pass")
            rows.append({
                "photo": path.name, "expected": expected, "passed": verdict.passed, "correct": ok,
                "seconds": round(seconds, 1), "reason": verdict.reason, "roast": verdict.roast,
            })
            print(f"{'✅' if ok else '❌'} {expected:4} {path.name:32} {seconds:5.1f}s  "
                  f"{verdict.reason}  | {verdict.roast}", flush=True)

    correct = sum(r["correct"] for r in rows)
    print(f"\n{verify.model_name()}: {correct}/{len(rows)} correct, "
          f"median {sorted(r['seconds'] for r in rows)[len(rows) // 2]}s per photo")
    if args.out:
        args.out.write_text(json.dumps({"model": verify.model_name(), "results": rows}, indent=2))
    return 0 if correct == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
