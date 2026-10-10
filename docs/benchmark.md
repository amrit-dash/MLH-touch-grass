# Benchmark

Real runs of `scripts/bench.py` with `gemma4:e4b` on Ollama 0.32, CPU only (4 cores, no GPU). Times will be much lower on a laptop with a GPU or Apple Silicon.

18 photos: 8 that should pass, 10 that should fail.

- 16 real photos from the [PASCAL VOC 2012](http://host.robots.ox.ac.uk/pascal/VOC/) train set (outdoor scenes, rooms, desks with monitors). Not redistributed here.
- 2 fakes made for this test: a field of cows pasted onto the monitors of a desk photo, and a close-up crop where the monitor fills the frame.

## Run 1: one prompt

**16/18.** Every real photo was right. Both fakes passed as "Grass confirmed".

## Run 2: screen check first, plus a second question for passes

The prompt now asks the model to look for a screen before anything else, and every photo that passes is asked one more narrow question about bezels and borders.

**18/18**, median 25.8s per photo (passes take 2 model calls).

| Photo | Should | Result | Time | Roast |
|---|---|---|---|---|
| 021_bus_lawn | pass | ✅ Grass confirmed. | 26.0s | You're lucky the bus isn't a Jira ticket, or you'd be stuck in endless review cycles. |
| 022_pond_boats | pass | ✅ Grass confirmed. | 30.8s | Hope the debugging process is as serene as this water. |
| 031_mountain_farm | pass | ✅ Grass confirmed. | 32.6s | You're taking your outdoor time, but maybe you should be taking your code to the wilderness. |
| 033_park | pass | ✅ Grass confirmed. | 24.0s | Hope your pull request is as sturdy as those horses' legs. |
| 050_field_cows | pass | ✅ Grass confirmed. | 34.0s | You've got a beautiful view, but maybe your code needs a little more greenery before it ships. |
| 056_meadow | pass | ✅ Grass confirmed. | 33.3s | Hope you didn't try to code using only the ambient light from those rocks. |
| 063_tower_sky | pass | ✅ Grass confirmed. | 25.8s | You're lucky the sky is so clear, or I'd have to tell you to go outside and find a better view. |
| 076_harbour_truck | pass | ✅ Grass confirmed. | 35.3s | You're lucky the sky is so blue today, or I'd have to deny you entry for being indoors. |
| 001_crt_desk | fail | ✅ That doesn't look like outside. | 23.3s | You're going to have to step outside before you can push that code, buddy. |
| 004_dual_monitors | fail | ✅ That's a picture of a screen. Nice try. | 22.1s | You're going to have to step outside before you can push that code, even if it's just to look at a picture of a nice tree. |
| 019_bike_lounge | fail | ✅ That doesn't look like outside. | 24.7s | You brought a bicycle into the office; maybe you should have just cycled outside. |
| 032_apartment | fail | ✅ That doesn't look like outside. | 22.0s | Your desk looks like a digital graveyard of unfinished features. |
| 034_living_room | fail | ✅ That doesn't look like outside. | 26.2s | You're so committed to the code, you've forgotten how to look at the actual trees. |
| 041_dining_room | fail | ✅ That doesn't look like outside. | 27.0s | You're trying to debug your life by setting up a fancy dinner party, aren't you? |
| 047_imac_desk | fail | ✅ That's a picture of a screen. Nice try. | 18.9s | Looks like you're trying to debug your life choices on that screen. |
| 064_bedroom | fail | ✅ That doesn't look like outside. | 23.4s | You look like you're waiting for a very important meeting about the perfect code commit. |
| composite_screen_closeup | fail | ✅ That's a picture of a screen. Nice try. | 24.2s | Hope the grass is as green as your commit history! |
| composite_screen_desk | fail | ✅ That's a picture of a screen. Nice try. | 17.7s | You're lucky the grass in that picture is greener than your commit history. |

## Caveats

- 18 photos is a small set, and the prompt was changed after seeing the 2 fakes fail. Treat 18/18 as "the known holes are closed", not as a measured accuracy.
- The fakes are composites with clean edges. Real photos of screens have glare and moire, which may be easier or harder.
- The model calls the cows "horses". It doesn't matter for the verdict.

## Reproduce

```sh
ollama pull gemma4:e4b
TOUCHGRASS_MODEL=gemma4:e4b python scripts/bench.py path/to/photos --out results.json
```

`scripts/e2e_phone.mjs` drives the real phone page with Playwright against a real `touchgrass prove` and real model.
