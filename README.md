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
ollama pull gemma4:e4b   # or gemma4:e2b on a smaller laptop
# (Homebrew's Ollama can't do JSON mode; touch-grass notices and parses plain replies)

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
| `touchgrass prove [--tunnel \| --public-url URL]` | Shows a QR code; your phone uploads a photo; the model judges it |
| `touchgrass log` | Your grass receipts |
| `touchgrass check` | What the hook runs: exits 1 when you're overdue |

## Settings

| Env var | Default | |
|---|---|---|
| `TOUCHGRASS_MAX_MINUTES` | `180` | Minutes indoors before pushes lock |
| `TOUCHGRASS_MODEL` | `gemma4:e4b` | Any Ollama vision model (`gemma4:e2b` is lighter) |
| `OLLAMA_HOST` | `http://localhost:11434` | |
| `TOUCHGRASS_HOME` | `~/.touchgrass` | State and receipts |
| `TOUCHGRASS_TUNNEL` | unset | `1` makes `prove` always use `--tunnel` |
| `TOUCHGRASS_PUBLIC_URL` | unset | Same as `--public-url` |

## Off your Wi-Fi

By default the phone page is on your LAN, so phone and laptop need the same Wi-Fi. To use mobile data, or a network that blocks devices talking to each other:

```sh
brew install cloudflared
touchgrass prove --tunnel
```

That opens a [Cloudflare quick tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/): a temporary `https://….trycloudflare.com` address, no account needed, gone when `prove` exits. The model still runs on your laptop. The photo travels to it through Cloudflare over HTTPS and isn't stored.

Already have your own HTTPS address (ngrok, Tailscale Funnel, a reverse proxy) forwarding to port 8765? Use `touchgrass prove --public-url https://your.address`.

In both modes the server only listens on `127.0.0.1` and the one-time token is 128 bits, because the URL is public.

## How it decides

1. **Fresh photo**: the capture time must be within the last 15 minutes. The page opens the camera directly, not the gallery.
2. **Describe**: the photo goes to the local model, which returns JSON: `photo_of_screen`, `outdoors`, `sky_or_plants`, a description and a roast.
3. **Decide**: plain Python, not the model, makes the call. Outdoors, sky or plants, and not a screen.
4. **Double-check passes**: anything that passed gets a second, narrower question: "is this scene on a monitor or a print?" The first prompt missed a monitor that filled the frame; this one catches it.

## Benchmark

`scripts/bench.py PHOTOS_DIR` runs the real pipeline over `PHOTOS_DIR/pass/*.jpg` and `PHOTOS_DIR/fail/*.jpg` and reports accuracy and time per photo. See [docs/benchmark.md](docs/benchmark.md) for results.

## Honest limits

`git push --no-verify` skips any hook. The capture time is reported by your phone's browser and can be faked. This is a nudge with a sense of humour, not a prison.

## Development

```sh
python -m unittest discover -s tests
```

## License

GPL-3.0
