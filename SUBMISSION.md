<!--
DRAFT of the DEV post. Writing quality is the most heavily weighted judging criterion.
Before publishing:
  - Start from the official submission template on the challenge page (it adds #devchallenge #hf26challenge).
  - Replace every [TODO] with real output from your own runs. Do not invent verdicts or roasts.
  - Add the demo video/GIF.
  - Rewrite in your own voice.
-->

# My `git push` won't work until I touch grass

*This is a submission for the [Hacktoberfest Open-Source AI Challenge: Week 1 — Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05).*

## What I Built

[TODO: one paragraph, first person. Suggested angle: you noticed you'd pushed 14 times today without standing up.]

**touch-grass** is a git pre-push hook. After three hours indoors, `git push` refuses:

```
🌱 touch-grass: 3h 12m since you last saw the sky. Push blocked.
```

To unlock it, run `touchgrass prove`, scan the QR code, walk outside and take a photo. An open-weight vision model running on my own laptop decides whether I actually went outside.

## Demo

[TODO: 30–60s video: blocked push → walk outside → photo → verdict on phone → push succeeds]

Repo: https://github.com/amrit-dash/MLH-touch-grass

## How It Gets People Outside

Most "go outside" apps suggest. This one gates. It sits on the one command a developer runs constantly and makes it conditional on daylight.

[TODO: what it actually felt like the first time it blocked you mid-task]

## How I Built It

- **Hook**: `touchgrass install` writes a `pre-push` hook. It compares now against your last verified outing.
- **Phone page**: `touchgrass prove` starts a tiny server on your LAN with a one-time token. The page opens the camera directly, downsizes the photo and sends it with its capture time.
- **Verification**: Gemma, via Ollama, gets the photo and returns JSON: `outdoors`, `sky_or_plants`, `photo_of_screen`, a description and a roast.
- **Receipt**: a pass resets the clock and saves a "grass receipt".

### The anti-cheat arms race

[TODO: the funny section. Try each of these for real and paste the actual verdicts:]
- [TODO: a photo of grass on your monitor]
- [TODO: a photo out the window]
- [TODO: an old photo from the gallery → rejected by the freshness check]
- [TODO: the real thing]

## Why Open Innovation Matters Here

This tool looks at photos of where you are. That's not something I want to send to someone else's API. Running Gemma locally means the photo, your location in it and your habits stay on your machine. It also means it's free to run as often as you push, and anyone can swap the model or change the rules.

## Limits

`git push --no-verify` exists. The capture time can be spoofed. It's a nudge with jokes, not a prison.

## Prize Categories

- Best Use of Gemma

<!-- Team: list DEV usernames if applicable -->
