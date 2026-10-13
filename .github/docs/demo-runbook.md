# Demo Runbook

A 3-to-4 minute recording of HotSpot Sentinels against the deployed stack. Every
number below was measured on **2026-10-13** against revision `d30ad26`, not estimated.

|               |                                                               |
| ------------- | ------------------------------------------------------------- |
| Dashboard     | https://hotspot-frontend-153692178986.asia-southeast1.run.app |
| Backend       | https://hotspot-backend-153692178986.asia-southeast1.run.app  |
| Alert wall    | https://hotspot-sentinels-7364.web.app                        |
| Region        | `asia-southeast1`                                             |
| Recording cap | **3 to 4 minutes** — target **3:30**                          |

## The cache risk is now largely retired

The imagery cache used to be in-process only. Cloud Run scales to zero, the
container died, and the cache died with it — so a coordinate warmed an hour
earlier returned a 502 from `/api/imagery` immediately after a perfectly
successful analysis.

`TASK-046` moved the cache to Cloud Storage, so imagery fetched by any instance is
served by every other one and survives scale-to-zero for 24 hours. Verified live:
a brand-new revision returned the 640×640 PNG a different instance had fetched.

Two consequences for recording:

- `--max-instances=1` is **no longer required**. Leave autoscaling alone.
- Both demo beats are now coordinates, so both depend on the Maps imagery cache.
  Warm both in the pre-flight. If one misbehaves, the upload fallback opener
  calls no Maps API at all and cannot be taken out by a cold cache.

The first fetch after a 24-hour gap re-requests from Maps and is slower, which is
why the pre-flight warms the opener as well as the contrast.

## Pre-flight

Run this within a few minutes of recording.

```bash
U=https://hotspot-backend-153692178986.asia-southeast1.run.app

# Generate the samples if data_samples/ is empty; they are not committed.
.venv/bin/python backend/tools/seed_samples.py

# Throwaway call to absorb the container cold start.
curl -sS -o /dev/null -X POST "$U/api/analyze" -F file=@data_samples/industrial_hotspot.jpg

# Warm the opener (Pasir Panjang Terminal) and the contrast (Botanic Gardens).
curl -sS -o /dev/null -X POST "$U/api/analyze" -F imagery_lat=1.2816 -F imagery_lng=103.7571
curl -sS -o /dev/null -X POST "$U/api/analyze" -F imagery_lat=1.3521 -F imagery_lng=103.8198

# Both must print 200.
curl -sS -o /dev/null -w 'pasir panjang  %{http_code}\n' "$U/api/imagery?lat=1.2816&lng=103.7571"
curl -sS -o /dev/null -w 'botanic gardens %{http_code}\n' "$U/api/imagery?lat=1.3521&lng=103.8198"

# All four dependencies must read "ready".
curl -sS "$U/api/health"
```

The opener run above publishes a CRITICAL alert, which adds a card to the public
wall. Rehearsals add more. To show a clean wall, trim duplicates first — or leave
them and call them repeat detections, which is what they are.

## Measured timings

Re-measured against the deployed stack on 2026-10-13.

| Step                                        | API only   | Notes                              |
| ------------------------------------------- | ---------- | ---------------------------------- |
| **Opener — Pasir Panjang Terminal**         | **21.6 s** | 3 runs: 22.5 / 21.4 / 20.8 s       |
| Fallback opener — industrial upload         | **17.2 s** | 3 runs: 17.4 / 17.5 / 16.7 s       |
| Contrast — Botanic Gardens coordinate       | **12.6 s** | 3 runs: 13.0 / 12.3 / 12.9 s       |
| **Total spent waiting (coordinate opener)** | **~34 s**  | ~30 s if you use the upload opener |
| First call after idle                       | **15.9 s** | cold start is now close to warm    |

The coordinate opener costs about twice the contrast, and that is not cold cache:
it reproduced at 25–27 s with imagery already cached. Budget for it. Either extend
the narration over the spinner, as the script below does, or cut the wait in the
edit — do not record it in silence.

That leaves roughly **170 seconds of a 210-second (3:30) target** for narration.
The rules allow 3 to 4 minutes while the submission template says 3 minutes, so
3:00–3:30 is the window that satisfies both; do not come in under 3:00. Add a few
seconds for UI rendering on top of the API figures.

The first analysis after an idle period used to be much the slower one. That gap
has closed: on 2026-10-13 the cold call took 15.9 s. Still run one throwaway
analysis before recording, but a cold start is no longer the hazard it was.

## Two openers now work — pick one and rehearse it

The old opener coordinate `1.2897, 103.7540` is **open sea**, which was only found
by fetching its imagery and looking at it. The model reads that dark water as
100% asphalt, scores it 9.1 CRITICAL and fires a real Pub/Sub alert. Do not use
it, and do not quote its 9.1 anywhere: it is a false positive, not a result.

The preset now points at **Pasir Panjang Terminal** itself, `1.2816, 103.7571`,
which is genuinely the container yard. Three consecutive runs on 2026-10-13:

```
HVI 8.6  CRITICAL  alert=True  asphalt 65%  dark roof 20%  concrete 15%  canopy 0%
zone: "Container Terminal and Car Storage"
```

So there are two viable openers. They are genuinely different arguments, not just
different numbers:

|             | Pasir Panjang Terminal                       | Industrial upload                            |
| ----------- | -------------------------------------------- | -------------------------------------------- |
| Score       | **8.6 CRITICAL**, 0% canopy                  | **8.6 CRITICAL**, 2% canopy                  |
| Imagery     | real Google satellite                        | synthetic sample                             |
| Time        | 26.1 s                                       | 17.2 s                                       |
| Shows       | it works on a **real place** you can look up | it reads **any** photo, no coverage needed   |
| Risk        | depends on the Maps imagery cache            | none — no Maps call at all                   |
| Coordinates | supplied, so honest                          | **inferred** — the model guesses Los Angeles |

The coordinate is the stronger opening claim: a judge can check Singapore's port
on a map. The upload is the safer one and sets up the honest-limits beat, because
the guessed Los Angeles coordinate is the evidence for it.

Recommended: **open with the coordinate** for impact, keep Botanic Gardens as the
contrast, and mention the inferred-coordinate caveat verbally rather than
spending a beat on the upload. If the imagery cache misbehaves during rehearsal,
fall back to the upload opener — the script works either way, only the number and
the surface mix change.

## What the page looks like on load

Verified against the deployed app on 2026-10-13. Nothing needs setting up on
camera — the dashboard opens ready to run the opener:

- **Location shortcut** is already on *Singapore Port Terminal*, and latitude and
  longitude already read `1.2816` and `103.7571`.
- **The map is already open** with the marker on that point. The picker no longer
  starts collapsed, so there is no expander to click.
- Both search boxes are present, one in the sidebar and one above the map.

So the opening move is simply **Run HotSpot Analysis**. Everything before that is
narration over a screen that is already in the right state.

The sidebar still collapses once a result renders. You do not need it again: the
map panel has its own search box, so the contrast location is chosen from the
main area.

## What to show from location discovery

These cost no analysis time — they are interactive, so only the two analyses
spend the clock. Verified on the deployed stack on 2026-10-13.

| Feature             | On camera                                                                                 |
| ------------------- | ----------------------------------------------------------------------------------------- |
| Shortcut list       | 15 Asian places ordered most built-up to most green, so the list itself is the risk scale |
| Place autocomplete  | Type three characters; a dropdown of real places appears, neighbourhoods included         |
| Synced search boxes | Choosing in one box updates the other, so the active location is never ambiguous          |
| Map click naming    | Click anywhere; the point is named (`Padang City, Indonesia`, `Mediterranean Sea`)        |
| Public alert wall   | A Firebase-hosted page where citizens see CRITICAL zones appear live                      |

The shortcut list is the cheapest reach proof there is: opening it shows Dhaka,
Kolkata, Manila, Mumbai, Bangkok, Tokyo, Delhi, Kuala Lumpur and Singapore in one
glance, graded from a container terminal at the top to a national park at the
bottom. It costs two seconds and no API call.

The alert wall is the pay-off for the Pub/Sub beat: it shows the alert reaching
someone outside the dashboard. Open it in a second tab **before** recording, so
the CRITICAL zone appears without a page reload.

## Script

Read this aloud. It is timed at a normal speaking pace (~150 wpm) and the two
waits are already budgeted. Target **3:30**; the hard window is 3:00–4:00.

Bracketed text is the action, not the words.

### 0:00–0:20 · The problem

> [Dashboard open, nothing run yet]
>
> "Heat is the deadliest weather there is — and cities make it worse. Dark roofs
> and asphalt turn a neighbourhood into an oven, several degrees hotter than the
> countryside around it. That heat kills the elderly, it kills street animals,
> and it drives air-conditioning demand that burns more carbon, which makes next
> summer hotter still.
>
> The problem isn't that we can't fix it. It's that nobody can point at a block
> and say *how bad is this one, and what exactly do I do about it?*
>
> HotSpot Sentinels answers that in about fifteen seconds."

### 0:20–0:38 · Reach: anywhere on earth

> [Open the **Location shortcut** dropdown. Scroll it slowly — Dhaka, Kolkata,
> Manila, Mumbai, Bangkok, Tokyo, Delhi, Kuala Lumpur. Close it again on
> *Singapore Port Terminal*, which is already selected.]
>
> "You can point it anywhere on earth. These are real places across Asia, and the
> list runs from the most built-up at the top to the greenest at the bottom —
> that ordering is the risk scale.
>
> You can also type any place name and it suggests as you go, click a point on
> the map, or paste coordinates. I'm starting with a working container port."

**Why the dropdown and not the search box:** the page already opens on Pasir
Panjang Terminal, so searching for it would be theatre. The dropdown proves reach
in two seconds with no API call and no typing to fumble. If you would rather show
the typeahead live, type `Pasir Panjang T` — shorter prefixes put a Malaysian
town first, because the suggestions are real Google Places results.

### 0:38–1:02 · Run it

> [Click Run. Satellite imagery appears. **This wait is ~22 s** — the longest in
> the video. The words below are written to fill it; do not rush them.]
>
> "That's live Google satellite imagery, pulled by the backend — not a stock
> photo. Gemini 2.5 Flash is reading the actual surface materials: what fraction
> is asphalt, what's dark roofing, concrete, tree canopy.
>
> At the same time the backend is querying NOAA's global weather archive in
> BigQuery for the real ambient temperature at that exact location. Not a
> simulation, not an average — measured data from the nearest station.
>
> And this is the part that matters for a city that can't afford a survey: there
> is no thermal camera here, no LiDAR, no drone flight. It is reading ordinary
> colour imagery that already exists for most of the planet. If your city is on
> a satellite map, you can do this today."

### 1:02–1:32 · The verdict

> [Result renders: HVI 8.6 CRITICAL, "Container Terminal and Car Storage"]
>
> "It has named it for what it is — a container terminal and car storage yard.
> Heat Vulnerability Index: **8.6 out of 10. Critical.**
>
> And here's why, which matters more than the number — sixty-five percent
> asphalt, twenty percent dark roofing, fifteen percent concrete. **Zero percent
> tree canopy.** Every surface in that frame absorbs heat through the day and
> radiates it back after dark, which is why places like this never cool down
> overnight.
>
> Because it crossed critical, the system didn't wait to be asked. It published
> an alert automatically."

### 1:30–1:50 · Proof the alert is real

> [Switch to the alert wall tab — the zone is already there]
>
> "This is a separate public page, and that zone is already on it. The alert went
> out over Pub/Sub, landed in Firestore, and reached citizens without anyone
> clicking send. Residents don't need access to the planning dashboard to find out
> their street is dangerous."

### 1:52–2:16 · The prescription

> [Back to dashboard, scroll to the passive cooling blueprint]
>
> "A score alone changes nothing. So it prescribes: orient the ventilation
> corridor to catch the prevailing wind. Coat **three hundred thousand square
> metres** in retroreflective material. Plant street trees, add shade structures,
> use cool pavements.
>
> Projected surface temperature drop: **seven degrees Celsius.** That is the
> difference between a heatwave that is survivable and one that is not — and a
> direct cut in the air-conditioning load that would otherwise burn more carbon."

### 2:15–2:45 · Proof it tracks reality

> [Search `Botanic` beside the map, pick Singapore Botanic Gardens, Run]
>
> "Now the control. Same model, same pipeline — but a real satellite view of the
> Singapore Botanic Gardens.
>
> **One point five. Low.** A hundred percent canopy, nothing to coat, one degree
> of headroom. The score isn't guessing a mood, it's tracking what's physically on
> the ground. And the gap between 8.6 and 1.5 *is* the intervention — that gap is
> what trees buy you."

### 2:45–3:05 · What it does not pretend to do

> [Stay on the result; no need to show anything specific]
>
> "One honest note. Every identity field in that report is labelled **supplied**
> or **inferred**. Give it a bare photo with no location and the model will guess
> the coordinates — and it can guess wrong. The system doesn't hide that, so a
> planner knows which numbers to trust.
>
> It also refuses junk before it spends anything — wrong file types, files
> disguised as images, oversized uploads. And if the climate archive is
> unreachable it falls back and says so on screen rather than inventing a
> temperature. This is a triage tool that tells you where to survey first. It
> doesn't replace the survey."

### 3:05–3:30 · Close

> [City map of analysed zones, then architecture slide or the repo]
>
> "Every zone analysed, on one map, coloured by risk — that's a city-wide
> retrofit queue, ordered worst-first.
>
> Gemini 2.5 Flash, Google Maps, BigQuery, Firestore, Pub/Sub and Firebase, all on
> Cloud Run in Singapore. Fifteen seconds and a photo, to find the block that's
> cooking people and tell you what to do about it.
>
> That's HotSpot Sentinels."

### Beat summary

| Time      | Beat          | Must land                                |
| --------- | ------------- | ---------------------------------------- |
| 0:00–0:20 | Problem       | Heat kills; nobody can rank a block      |
| 0:20–0:35 | Reach         | Any place on earth, three ways           |
| 0:35–1:02 | Run           | Gemini + real NOAA data, no thermal kit  |
| 1:02–1:32 | Verdict       | **8.6 CRITICAL**, 65% asphalt, 0% canopy |
| 1:30–1:50 | Alert wall    | The alert actually reached people        |
| 1:50–2:15 | Blueprint     | 10,000 m², **10 °C** drop                |
| 2:15–2:45 | Contrast      | **1.5 LOW** — trees are the fix          |
| 2:45–3:05 | Honest limits | inferred vs supplied, guard rails        |
| 3:05–3:30 | Close         | Architecture + the one-line pitch        |

If it runs long, cut the city map sentence first, then trim the problem statement.
**Do not cut the alert wall or the honest-limits beat** — the first proves the
alert is real, and the second is what separates this from a demo that overclaims.

## Recording setup

| Setting    | Value                                                                |
| ---------- | -------------------------------------------------------------------- |
| Resolution | 1920×1080, browser at 100% zoom                                      |
| Window     | Hide bookmarks and extra tabs; keep only dashboard + alert wall tabs |
| Tool       | QuickTime (macOS, free) or OBS. Record screen + mic together         |
| Mic        | Anything but laptop speakers-adjacent; test one 10-second take first |
| Cursor     | Move deliberately and slowly; judges follow your pointer             |

Two tabs, in this order: **1** dashboard, **2** alert wall — opened *before* you
start so the alert appears on it without a reload.

If you would rather not narrate live, record the screen silently, then add the
script as captions or a voiceover afterwards. The timings above hold either way.

## Post-production checklist

- [ ] Length is between 3:00 and 4:00
- [ ] The HVI number you say matches the number on screen
- [ ] No API keys, account pickers, or personal tabs visible in any frame
- [ ] The two analysis waits are either narrated over or cut
- [ ] Audio is audible without headphones
- [ ] Upload, set to public or unlisted, and paste the URL into the submission deck

## Scripted scenarios

| Scenario        | Input                           | Expected                           |
| --------------- | ------------------------------- | ---------------------------------- |
| Critical opener | coordinate 1.2816, 103.7571     | HVI 8.6 CRITICAL, alert dispatched |
| Fallback opener | upload `industrial_hotspot.jpg` | HVI 8.6 CRITICAL, alert dispatched |
| Low contrast    | coordinate 1.3521, 103.8198     | HVI 1.5 LOW, no alert              |

Each reproduced identically on three consecutive runs on 2026-10-13. They are
inferred by the model, not hardcoded, so treat them as highly likely rather than
guaranteed. Generate the samples with `.venv/bin/python backend/tools/seed_samples.py`
if `data_samples/` is empty — they are not committed.

### What the scenarios actually return

Measured 2026-10-13, each on three consecutive runs. These are the numbers the
narration quotes.

| Field                   | Opener (coordinate)                | Fallback (upload)                | Contrast (coordinate) |
| ----------------------- | ---------------------------------- | -------------------------------- | --------------------- |
| Input                   | 1.2816, 103.7571                   | `industrial_hotspot.jpg`         | 1.3521, 103.8198      |
| Zone name               | Container Terminal and Car Storage | Industrial Hotspot               | Dense Tropical Forest |
| HVI / band              | **8.6 CRITICAL**                   | **8.6 CRITICAL**                 | **1.5 LOW**           |
| Asphalt / dark roof     | 65% / 20%                          | 38% / 55%                        | 0% / 0%               |
| Concrete / green canopy | 15% / **0%**                       | 5% / **2%**                      | 0% / **100%**         |
| Ambient (source)        | 31.0 °C (`bigquery`)               | 31.0 °C (`bigquery` — real NOAA) | 31.0 °C (`bigquery`)  |
| Retroreflective coating | **300,000 m²**                     | 4,000 m²                         | 0 m²                  |
| Projected temp drop     | **7.0 °C**                         | 8.0 °C                           | 1.0 °C                |
| Alert dispatched        | **true**                           | **true**                         | false                 |
| Coordinate provenance   | supplied                           | **inferred** (model guessed LA)  | supplied              |
| Latency                 | 21.6 s                             | 17.2 s                           | 12.6 s                |

The canopy pair is the whole environmental argument in two numbers: **0% canopy
scores 8.6 CRITICAL, 100% canopy scores 1.5 LOW**, same model and same pipeline.
Lead with it.

### Honest-limits beat — verified evidence

Every claim in the 2:45 beat was checked live on 2026-10-13. Show any of these on
screen only if you have time; the narration stands without them.

| Claim                               | Check                                           | Result     |
| ----------------------------------- | ----------------------------------------------- | ---------- |
| Rejects non-images                  | upload a `.txt`                                 | `415`      |
| Rejects files disguised as images   | text bytes named `.png` with `image/png` header | `415`      |
| Refuses oversize before model spend | 11 MB upload                                    | `413`      |
| Says so when a place does not exist | `/api/geocode?q=Nonexistentplacexyz`            | `404`      |
| Labels guessed identity             | upload report `identity_source.coordinates`     | `inferred` |

The inferred-coordinate point is the strongest of these. Given a synthetic aerial
photo with no metadata, the model placed it at `34.0522, -118.2437` — Los Angeles.
The system records that as `inferred` rather than presenting it as fact. Saying
this out loud costs nothing and buys credibility that an overclaiming demo cannot.

## Fallbacks

| If this happens                                  | Do this                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Imagery missing, "attribution image unavailable" | Cache went cold. Rerun the two warm-up calls, reload, re-record that take.                                                                                                                                                                                                                                                 |
| Analysis exceeds ~30 s                           | Cold start. Run one throwaway analysis first, then record.                                                                                                                                                                                                                                                                 |
| `/api/health` reports `degraded`                 | Read which dependency is down. Analysis still works if `gemini` is ready; climate falls back to 38.5 °C and the UI labels it as a fallback.                                                                                                                                                                                |
| Coordinate returns 502                           | That coordinate has no cached image. Use the other scenario and warm the failing one again.                                                                                                                                                                                                                                |
| Analysis returns 502                             | The model occasionally returns a payload that fails schema validation; one run in four did so on 2026-10-04. The backend correctly refuses it rather than showing a malformed report. Simply run it again — two immediate retries both succeeded. Do a throwaway run before recording so a retry is not your opening shot. |
| Score differs from the table                     | Not a failure — the model re-reads the image. Narrate the score actually shown; the band is what matters.                                                                                                                                                                                                                  |
| Dashboard unreachable                            | Check the frontend revision is serving: `gcloud run services describe hotspot-frontend --region asia-southeast1`.                                                                                                                                                                                                          |

## Reset between takes

No reset is required. Every run appends a scan to Firestore and the dashboard
reads the most recent ones, so repeated takes are additive and harmless. To see a
clean "Recent municipal audits" list, simply do not press Refresh.

## After recording

Nothing to undo. Both services already run at `maxScale=3` and the demo no longer
pins `--max-instances=1`, so there is no demo-time setting left to restore.

Two things worth doing:

- **Trim the public alert wall.** Every rehearsal that scores CRITICAL adds a
  card, and they stack up as duplicates of the same zone.
- **Paste the video URL into slide 14** of `HotSpot_Sentinels_Submission.pptx`,
  which is the last remaining placeholder in the deck.
