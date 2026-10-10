# touch-grass

Hacktoberfest 2026 DEV challenge entry (Week 1, "Touch Grass"). A git pre-push hook that blocks pushes after N minutes indoors until a phone photo, judged by a local Gemma 4 model via Ollama, shows you went outside.

- Challenge facts, strategy and timeline: `PLAN.md`
- DEV post draft (in Amrit's voice, `[TODO]`s need real results): `SUBMISSION.md`
- Benchmark results and caveats: `docs/benchmark.md`

## Code

- `touchgrass/cli.py`: `install`, `check` (the hook), `prove`, `status`, `log`
- `touchgrass/server.py`: LAN server for the phone page, one-time token in the URL
- `touchgrass/verify.py`: freshness check, model prompts, `judge()` (plain Python decides), `check()` = describe + second screen check on passes
- `touchgrass/page.html`: phone camera page
- `scripts/bench.py`: real-model benchmark over `DIR/pass` and `DIR/fail`
- `scripts/e2e_phone.mjs`: Playwright drives the phone page against real `prove` + model

No runtime dependencies. `qrcode` is optional (`.[qr]`).

## Commands

```sh
python -m unittest discover -s tests          # unit tests, no model needed
TOUCHGRASS_MODEL=gemma4:e4b python scripts/bench.py PHOTOS_DIR
```

## Rules

- Never invent model verdicts, roasts or benchmark numbers for the post or docs. Only paste real output.
- Don't commit third-party photos (e.g. PASCAL VOC). Use photos the author took.
- Post text: no em dashes, short paragraphs, contractions, first person.
