# Hacktoberfest 2026 — DEV Week 1 "Touch Grass": plan

## The challenge (as of 2026-10-09)

| | |
|---|---|
| Challenge | Hacktoberfest Open-Source AI Challenge: Week 1 — **Touch Grass** |
| Page | https://dev.to/challenges/hacktoberfest-week1-2026-10-05 |
| Rules | https://dev.to/page/hacktoberfest-week1-2026-10-05-contest-rules |
| Deadline | **October 11, 2026** (confirm the timezone on the rules page; DEV usually uses US time) |
| Prompt | Build a *new* project with open-source AI at its core (open-weight models, open agent frameworks, local inference) that gets people off their screens and into the world |
| Submission | A DEV post using the challenge template, tags `#devchallenge #hf26challenge`. Must cover: what you built, how it gets people outside, a demo, why open innovation matters for it |
| Prizes | 17 winners: 1 overall ($250 + DEV++ + badge), 16 partner categories ($100–$200 + badge). **Max one prize per person** |
| Judging | **Writing quality (weighted most)**, relevance to theme, creativity, technical execution, partner tech use (categories only) |
| Partner categories | Featured: Render, TabPFN, Tinker, Arduino, DigitalOcean, Gemma. Others: Backboard, ElevenLabs, Entire, GitHub Copilot, Mastra, MongoDB Atlas, Sentry, SerpApi, Temporal, Tiger Data |
| Credits | Tinker, Render, Backboard, ElevenLabs credits/promo codes via https://hacktoberfest.com/my (log in with your MLH account) |
| PRs | Do **not** count this year. Repo must be created and finished inside the entry window |

Weeks 2–4 (Oct 12–18, 19–25, 26–31) are separate challenges with new themes. Each needs a *new* project, so this one can't be recycled.

Caveat: dev.to and hacktoberfest.com were blocked from the build environment, so the table comes from search-indexed copies of those pages. Re-read the rules page before submitting.

## What the competition looks like

Searching `#hf26challenge` shows the obvious idea is already taken many times over: "TouchGrass AI", "Nature Quest", "Side Quests", "WildLens", "FloraFind" — almost all are *an LLM generates outdoor quests / identifies plants* in a PWA. Another one of those loses on creativity and is hard to make the writing stand out.

## Ideas considered

| Idea | Theme fit | Novelty vs. field | Buildable by Oct 11 | Verdict |
|---|---|---|---|---|
| AI outdoor quest generator | High | **Low** (10+ entries) | Yes | Skip |
| Plant/bird ID walk companion | High | Low | Yes | Skip |
| Arduino soil sensor you literally touch | High, funny | High | Only if you own the hardware | Backup if you have an Arduino |
| TabPFN "burnout predictor" from commit history | Medium | Medium | Yes | Gimmicky; weak "outside" story |
| **`touch-grass`: git pre-push hook that blocks your push until a local Gemma vision model verifies a photo of you outside** | High | **High** — aimed at developers, the DEV audience | Yes, small scope | **Build this** |

## The pick: `touch-grass`

You've been coding for 3 hours straight. `git push` refuses:

```
🌱 touch-grass: 3h 12m since you last saw the sky. Push blocked.
   Run `touchgrass prove`, scan the QR code, take a photo outside.
```

Your phone opens a camera-only page served from your laptop. You walk outside, snap a photo, and a **local open-weight model (Gemma via Ollama)** judges it: is this outdoors, is there sky or plants, is it a photo of a screen? Pass → push unlocked, and you get a "grass receipt" with a one-line roast from the model. Fail → the model tells you why ("That is a monitor displaying a meadow.").

Why it should score well:
- **Theme**: the whole product is a forcing function to physically go outside.
- **Creativity**: inverts the genre. Not an app that *suggests* going outside — a dev tool that *gates* your work on it.
- **Open AI at the core**: the vision verification only works because a model runs locally. No photo of you or your surroundings ever leaves your machine. That is the "why open innovation matters" section of the post, and it's a real argument, not filler.
- **Writing**: dev humour + a clear story (the anti-cheat arms race: screenshots, photos of screens, old gallery photos) makes a good post.

Honest limits to state in the post: `git push --no-verify` bypasses it. It's a nudge, not a prison.

### Prize category

Primary: **Best Use of Gemma** (the model is the core of the product). It's also likely the most crowded category. You can only win once anyway, so list every category you genuinely use and no others.

Optional add-on if time allows (only if it's real, not bolted on):
- **ElevenLabs**: speak the roast/receipt out loud. Not open-weight, so keep it optional and off the core path.

### Scope

MVP (done in this repo):
- `touchgrass install` — installs the git pre-push hook
- `touchgrass check` — hook entry point; blocks if time since last verified grass > threshold
- `touchgrass prove` — local HTTP server + QR code; phone camera upload; Gemma verdict; writes receipt
- `touchgrass status`, `touchgrass log` — receipts history
- Anti-cheat: camera-only capture input, EXIF timestamp freshness, model checks for photos of screens

Stretch (only after the post is drafted):
- Weekly "grass report" from receipts
- Team mode: show teammates' grass streaks
- Tray/menubar reminder before you hit the push wall

### Timeline (Melbourne time; deadline is likely US time, which buys extra hours — confirm)

| When | What |
|---|---|
| Fri Oct 9 | MVP code (done), install Ollama + `gemma3:4b` locally, run it end to end |
| Sat Oct 10 AM | Real demo: record a 30–60s screen + phone capture (blocked push → walk outside → photo → unlocked). Collect 3–4 funny verdicts, including a failed cheat attempt |
| Sat Oct 10 PM | Write the DEV post (draft in `SUBMISSION.md`). This is the top-weighted criterion — give it at least as much time as the code |
| Sun Oct 11 | Polish README, publish post with template + tags + Prize Categories section, before the deadline |

### Post outline (draft in SUBMISSION.md)

1. Hook: the push that refused.
2. What I built + demo GIF/video.
3. How it gets you outside: the push wall, the walk, the receipt.
4. How it works: hook → local server → phone camera → Gemma on Ollama → verdict JSON.
5. The anti-cheat arms race (screenshots, photos of screens, old photos) — the funny section.
6. Why open matters: a model that sees your surroundings should run on your machine.
7. Limits and what's next.
8. Prize Categories: Best Use of Gemma.

## To-do for you (can't be done from the build environment)

- [ ] Log in at https://hacktoberfest.com/my, register, claim credits
- [ ] Re-read the official rules page and confirm the deadline timezone
- [ ] Install Ollama, `ollama pull gemma3:4b`, run the end-to-end demo
- [ ] Record the demo
- [ ] Publish the DEV post
