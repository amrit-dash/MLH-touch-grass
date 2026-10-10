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

For the past couple of weeks I've been losing track of time. I'd look up, see 1 o'clock, and honestly not know if it was the afternoon or the middle of the night.

I was so deep in a project that I'd stopped taking breaks. That's what made me build **touch-grass**. It's a git pre-push hook. After 3 hours indoors (you can change that), this happens. Here's a real one from testing, with the limit set to 1 minute:

```
$ git push

🌱 touch-grass: 9m since you last saw the sky. Push blocked.
   Run `touchgrass prove`, scan the code with your phone and take a photo outside.
   (Yes, `git push --no-verify` works. You'll know.)
```

To get your push back, you run `touchgrass prove`. It prints a QR code. You scan it, your phone opens the camera, and you go outside and take a photo.

Then **Gemma 4, running on your own laptop**, looks at it and decides if it counts.

## Demo

I didn't record a video, so here's a real `prove` run from testing instead. I ran it over the tunnel, scanned the code and walked outside:

```
$ touchgrass prove --tunnel
📱 On your phone (anywhere), open:
   https://….trycloudflare.com/?t=…
   Model: gemma4:e4b via http://localhost:11434
   Waiting for a photo of the outside world… (Ctrl+C to give up)

✅ Grass confirmed. A hilly landscape with scattered houses under a cloudy sky.
   "It looks like you've found a much better environment to debug than your IDE."
   Push unlocked.
```

<!-- ADD 2 or 3 of your phone screenshots here: the laundry pass, the monitor that fooled it, the hillside pass. -->

Code: https://github.com/amrit-dash/MLH-touch-grass

## How It Gets People Outside

Every "go outside" app I've tried sends a notification. I swipe it away in under a second.

This one sits on the command I run 20 times a day. I can't swipe it away. The only way past it (well, the honest way) is the front door.

And it's tiny. You don't need a hike. You need sky or a plant in frame, taken in the last 15 minutes. That's a 2 minute walk, which is exactly the break I wasn't taking.

I built it, set it up, and promptly forgot about it. Then a push got blocked, and when I looked up from the screen the sun was setting outside.

## How I Built It

It's about 700 lines of Python plus one HTML page, with zero required dependencies.

1. **The hook.** `touchgrass install` writes a `pre-push` hook. It compares now against the last time a photo passed.
2. **The phone page.** `touchgrass prove` starts a small server on your Wi-Fi with a one-time token in the URL. The page opens the rear camera directly (`capture="environment"`), shrinks the photo to 1024px and sends it with its capture time. Not on the same Wi-Fi? `touchgrass prove --tunnel` gives the page a temporary HTTPS address through a Cloudflare quick tunnel, so it works on mobile data too.
3. **The check.** The photo goes to Gemma through Ollama, on `localhost`. The prompt asks for JSON only: `outdoors`, `sky_or_plants`, `photo_of_screen`, a one line description and a roast.
4. **The verdict.** Plain Python decides, not the model. Outdoors, plus sky or plants, plus not a screen.
5. **The double check.** Anything that passes gets one more question about screens (more on that below). Then the clock resets and you get a "grass receipt" (`touchgrass log`).

I kept the decision in code on purpose. The model describes the photo, and 3 lines of `if` decide what that means. Easier to test, and the model can't be talked into saying "pass".

### Can you cheat it?

Obviously that was the first thing I tried.

| Cheat | What stops it |
|---|---|
| Old photo from the gallery | Capture time has to be within 15 minutes |
| Photo out the window | Prompt says "not through a window" (I haven't tested this one yet) |
| Grass wallpaper on your monitor | `photo_of_screen`, plus the bezel double check |
| A monitor so close it fills the whole frame | Nothing, yet. Keep reading. |
| `git push --no-verify` | Nothing. You'll know. |

I also benchmarked it so I wasn't just trusting vibes. 18 labelled photos: 8 real outdoor scenes, 8 indoor rooms and desks, and 2 fakes where I pasted a field of cows onto a monitor in a desk photo.

The first run got **16 out of 18**. Every real photo was right. Both fakes sailed through as "Grass confirmed", with the roast "Hope the grass is as green as your commit history!" (rude, and also wrong).

So I changed 2 things. The prompt now makes the model look for a screen *before* it looks at the scene. And any photo that passes gets asked one more, much narrower question: what's at the edges of this photo, is it a bezel? Small models are bad at noticing a monitor frame when they're busy describing cows. They're good at it when that's the only question.

Second run: **18 out of 18**, about 26 seconds a photo on a 4 core CPU with no GPU. Full results are in [docs/benchmark.md](https://github.com/amrit-dash/MLH-touch-grass/blob/main/docs/benchmark.md).

(18 photos is tiny, and I fixed the prompt after seeing the fakes fail, so read that as "known holes closed", not "perfect". Also it calls the cows horses every single time.)

Then I tried it for real, with my own phone.

The first real photo, outside my building:

> ✅ Grass confirmed. A multi-story residential building with laundry hanging out to dry is visible under a blue sky.
> "It looks like your deployment is stuck waiting for the laundry cycle to finish."

Fair.

Then I put a photo of a grass field on my monitor and held my phone close enough that the grass filled the whole frame. No bezel, no desk.

> ✅ Grass confirmed. A vibrant green field of tall grass stretches towards a line of trees under a cloudy sky.
> "Hope your code is as lush and green as this field, or you'll be debugging in the weeds."

It got me. Both checks missed it.

When I tried again and a sliver of the browser bar crept into the corner, it caught me straight away:

> ❌ That's a picture of a screen. Nice try.

I retook the full-frame shot, saved it and tried 4 different screen prompts on it, with and without Gemma's thinking turned on. Every one said it was a real field. Once the screen fills the frame there isn't much left to see, just slightly too-green grass.

So that's the known hole. If you're willing to press your phone against your monitor to dodge a 2 minute walk, you win. You'll know, though.

And the hillside in the demo above went through the new HTTPS tunnel, first try.

## Why Open Matters Here

This thing looks at photos of where you are. Your street, your backyard, maybe your face.

I don't want that going to someone else's API every time I push code. With an open-weight model the only thing that ever looks at it is my laptop. (With `--tunnel` the photo passes through Cloudflare on the way, encrypted, but nobody else's model sees it and nothing stores it.) It also costs nothing per check, works offline, and if you think my rules are too strict you can change the prompt or swap the model in one env var.

## What's Missing

- `--no-verify` skips it. It's a nudge with jokes, not a prison.
- The capture time comes from the phone's browser, so a determined cheater can fake it.
- A screen held close enough to fill the whole frame gets through. I couldn't prompt my way out of that one.
- Same Wi-Fi by default. `--tunnel` fixes that, but then the photo goes through Cloudflare.

## Prize Categories

- Best Use of Gemma
