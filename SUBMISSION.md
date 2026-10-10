<!--
DRAFT of the DEV post. Paste into the official submission template on the challenge page
(it adds #devchallenge #hf26challenge), then:
  - Replace every [TODO] with your own runs. Don't invent verdicts or roasts.
  - Add the demo video and the screenshots in docs/.
  - Read it out loud once. If a line doesn't sound like you, change it.
-->

# I made `git push` refuse to work until I touch grass

*This is a submission for the [Hacktoberfest Open-Source AI Challenge: Week 1, Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05).*

## What I Built

[TODO: one or two lines, true to you. Something like: "I checked my screen time on Friday. It was 11h 40m. I'd been outside for the walk from the car to the office."]

So I built **touch-grass**. It's a git pre-push hook. After 3 hours, this happens:

```
$ git push

🌱 touch-grass: 3h 12m since you last saw the sky. Push blocked.
   Run `touchgrass prove`, scan the code with your phone and take a photo outside.
   (Yes, `git push --no-verify` works. You'll know.)
```

To get your push back, you run `touchgrass prove`. It prints a QR code. You scan it, your phone opens the camera, and you go outside and take a photo.

Then **Gemma 4, running on your own laptop**, looks at it and decides if it counts.

## Demo

[TODO: 30 to 60 second video. Blocked push, walk outside, photo, verdict on the phone, push goes through.]

<!-- Add 2 or 3 phone screenshots from YOUR run: the start screen (docs/phone-1-start.png), a rejected cheat, and a pass. -->

Code: https://github.com/amrit-dash/MLH-touch-grass

## How It Gets People Outside

Every "go outside" app I've tried sends a notification. I swipe it away in under a second.

This one sits on the command I run 20 times a day. I can't swipe it away. The only way past it (well, the honest way) is the front door.

And it's tiny. You don't need a hike. You need sky or a plant in frame, taken in the last 15 minutes. That's a 2 minute walk, which is exactly the break I wasn't taking.

[TODO: what actually happened the first time it blocked you mid-task]

## How I Built It

It's about 500 lines of Python plus one HTML page, with zero required dependencies.

1. **The hook.** `touchgrass install` writes a `pre-push` hook. It compares now against the last time a photo passed.
2. **The phone page.** `touchgrass prove` starts a small server on your Wi-Fi with a one-time token in the URL. The page opens the rear camera directly (`capture="environment"`), shrinks the photo to 1024px and sends it with its capture time.
3. **The check.** The photo goes to Gemma through Ollama, on `localhost`. The prompt asks for JSON only: `outdoors`, `sky_or_plants`, `photo_of_screen`, a one line description and a roast.
4. **The verdict.** Plain Python decides, not the model. Outdoors, plus sky or plants, plus not a screen.
5. **The double check.** Anything that passes gets one more question about screens (more on that below). Then the clock resets and you get a "grass receipt" (`touchgrass log`).

I kept the decision in code on purpose. The model describes the photo, and 3 lines of `if` decide what that means. Easier to test, and the model can't be talked into saying "pass".

### Can you cheat it?

Obviously that was the first thing I tried.

| Cheat | What stops it |
|---|---|
| Old photo from the gallery | Capture time has to be within 15 minutes |
| Photo out the window | Prompt says "not through a window" [TODO: test this for real] |
| Grass wallpaper on your monitor | `photo_of_screen` |
| `git push --no-verify` | Nothing. You'll know. |

I also benchmarked it so I wasn't just trusting vibes. 18 labelled photos: 8 real outdoor scenes, 8 indoor rooms and desks, and 2 fakes where I pasted a field of cows onto a monitor in a desk photo.

The first run got **16 out of 18**. Every real photo was right. Both fakes sailed through as "Grass confirmed", with the roast "Hope the grass is as green as your commit history!" (rude, and also wrong).

So I changed 2 things. The prompt now makes the model look for a screen *before* it looks at the scene. And any photo that passes gets asked one more, much narrower question: what's at the edges of this photo, is it a bezel? Small models are bad at noticing a monitor frame when they're busy describing cows. They're good at it when that's the only question.

Second run: **18 out of 18**, about 26 seconds a photo on a 4 core CPU with no GPU. Full results are in [docs/benchmark.md](https://github.com/amrit-dash/MLH-touch-grass/blob/main/docs/benchmark.md).

(18 photos is tiny, and I fixed the prompt after seeing the fakes fail, so read that as "known holes closed", not "perfect". Also it calls the cows horses every single time.)

[TODO: your own cheat attempts with the real verdicts. These are the best part of the post.]

## Why Open Matters Here

This thing looks at photos of where you are. Your street, your backyard, maybe your face.

I don't want that going to someone else's API every time I push code. With an open-weight model it never leaves my laptop. It also costs nothing per check, works offline, and if you think my rules are too strict you can change the prompt or swap the model in one env var.

## What's Missing

- `--no-verify` skips it. It's a nudge with jokes, not a prison.
- The capture time comes from the phone's browser, so a determined cheater can fake it.
- Your phone and laptop need to be on the same Wi-Fi.

## Prize Categories

- Best Use of Gemma

<!-- Team: list DEV usernames if applicable -->
