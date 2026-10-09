# 🌱 touch-grass

A git pre-push hook that won't let you push until a local open-weight model has seen you outside.

```
$ git push
🌱 touch-grass: 3h 12m since you last saw the sky. Push blocked.
   Run `touchgrass prove`, scan the code with your phone and take a photo outside.
```

`touchgrass prove` serves a camera-only page on your Wi-Fi. Walk outside, take a photo, and **Gemma running on your own laptop via Ollama** decides whether it counts: is it outdoors, is there sky or plants, is it a photo of a screen? Pass, and your push is unlocked, with a grass receipt and a one-line roast. The photo never leaves your network.

Built for the [Hacktoberfest 2026 DEV Open-Source AI Challenge, Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05).

## Setup

```sh
# 1. A local vision model
ollama pull gemma3:4b

# 2. touch-grass
pip install "touchgrass[qr] @ git+https://github.com/amrit-dash/MLH-touch-grass"

# 3. In any repo you want to guard
touchgrass install
```

## Commands

| Command | What it does |
|---|---|
| `touchgrass install [--force]` | Installs the pre-push hook in the current repo |
| `touchgrass status` | How long you've been indoors and when pushes lock |
| `touchgrass prove` | Shows a QR code; your phone uploads a photo; the model judges it |
| `touchgrass log` | Your grass receipts |
| `touchgrass check` | What the hook runs: exits 1 when you're overdue |

## Settings

| Env var | Default | |
|---|---|---|
| `TOUCHGRASS_MAX_MINUTES` | `180` | Minutes indoors before pushes lock |
| `TOUCHGRASS_MODEL` | `gemma3:4b` | Any Ollama vision model |
| `OLLAMA_HOST` | `http://localhost:11434` | |
| `TOUCHGRASS_HOME` | `~/.touchgrass` | State and receipts |

## How it decides

1. **Fresh photo**: the capture time must be within the last 15 minutes. The page opens the camera directly, not the gallery.
2. **Model check**: the photo goes to the local model with a prompt asking for JSON: `outdoors`, `sky_or_plants`, `photo_of_screen`, a description and a roast.
3. **Verdict**: pass only if it's outdoors, shows sky or plants, and isn't a photo of a screen.

## Honest limits

`git push --no-verify` skips any hook. The capture time is reported by your phone's browser and can be faked. This is a nudge with a sense of humour, not a prison.

## Development

```sh
python -m unittest discover -s tests
```

## License

GPL-3.0
