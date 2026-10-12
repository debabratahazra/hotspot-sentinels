# Demo Runbook

A 3-to-4 minute recording of HotSpot Sentinels against the deployed stack. Every number
below was measured on 2026-10-04, not estimated.

|               |                                                               |
| ------------- | ------------------------------------------------------------- |
| Dashboard     | https://hotspot-frontend-153692178986.asia-southeast1.run.app |
| Backend       | https://hotspot-backend-153692178986.asia-southeast1.run.app  |
| Alert wall    | https://hotspot-sentinels-7364.web.app                        |
| Region        | `asia-southeast1`                                             |
| Recording cap | **3 to 4 minutes** — target **3:15**                          |

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
- The opener is an upload and never calls the Maps API at all, so the CRITICAL
  result and the alert cannot be taken out by a cold cache either way.

Still warm the contrast coordinate before recording. The first fetch after a
24-hour gap re-requests from Maps and is slower.

## Pre-flight

Run this within a few minutes of recording.

```bash
U=https://hotspot-backend-153692178986.asia-southeast1.run.app

# Generate the sample if data_samples/ is empty; it is not committed.
python backend/seed_samples.py

# Throwaway call to absorb the container cold start (36 s cold vs 15 s warm).
curl -sS -o /dev/null -X POST "$U/api/analyze" -F file=@data_samples/industrial_hotspot.jpg

# Warm the contrast coordinate.
curl -sS -o /dev/null -X POST "$U/api/analyze" -F imagery_lat=1.3521 -F imagery_lng=103.8198

# Must print 200.
curl -sS -o /dev/null -w 'botanic gardens %{http_code}\n' "$U/api/imagery?lat=1.3521&lng=103.8198"

# All four dependencies must read "ready".
curl -sS "$U/api/health"
```

## Measured timings

Re-measured against the deployed stack on 2026-10-05. **The opener changed** — see
"The port terminal no longer reaches CRITICAL" below.

| Step                                 | API only   | Notes                        |
| ------------------------------------ | ---------- | ---------------------------- |
| Opening analysis (industrial upload) | **15.0 s** | 3 runs: 15.0 / 14.9 / 15.9 s |
| Contrast analysis (Botanic Gardens)  | **13.4 s** | unchanged from 2026-10-04    |
| **Total spent waiting**              | **~28 s**  |                              |

That leaves roughly **167 seconds of a 195-second (3:15) target** for narration.
The rules allow 3 to 4 minutes while the submission template says 3 minutes, so
3:00–3:30 is the window that satisfies both; do not come in under 3:00. Add a few
seconds for UI rendering on top of the API figures. Either narrate over the spinner
or cut the wait in the edit; do not record it in silence.

The first analysis after an idle period is the slow one: it pays a container cold
start. Run one throwaway analysis before recording — the measured cold start on
2026-10-05 was 36 s against 15 s warm.

## The port terminal no longer reaches CRITICAL

The previous opener analysed coordinate `1.2897, 103.7540` and was documented at
HVI 8.7 CRITICAL with an alert dispatched. **That no longer reproduces.** Four
consecutive runs on 2026-10-05 returned:

```
HVI 6.7  HIGH  alert=False  concrete 100%
```

Stable, not variance. CRITICAL requires HVI >= 8.0 (`RISK_BANDS` in
`vision_analyzer.py`), so at 6.7 **no Pub/Sub alert fires** and the demo loses its
climax. The imagery the Maps Static API serves for that coordinate now reads as
uniform concrete apron rather than the asphalt-and-dark-roof mix scored earlier.

The opener is therefore the **uploaded industrial sample**, which returned HVI 8.1
CRITICAL with `alert_dispatched=true` on three consecutive runs, in half the time,
and — because it never calls the Maps API — carries none of the cache risk above.
The coordinate path still features as the contrast beat, so the Maps integration
is still demonstrated.

## Flow gotcha

The sidebar collapses once a result renders. That used to force a fumbly reopen
with the `»` control to reach the Location shortcut. It no longer does: the map
panel carries its own search box, so the contrast location can be chosen from the
main area without touching the sidebar. Use that path on camera.

## What to show from location discovery

These cost no analysis time — they are interactive, so only the two analyses
spend the clock. All were verified against the deployed stack on 2026-10-12.

| Feature             | On camera                                                                          |
| ------------------- | ---------------------------------------------------------------------------------- |
| Place autocomplete  | Type three characters; a dropdown of real places appears, neighbourhoods included   |
| Synced search boxes | Choosing in one box updates the other, so the active location is never ambiguous    |
| Map click naming    | Click anywhere; the point is named (`Padang City, Indonesia`, `Mediterranean Sea`)  |
| Public alert wall   | A Firebase-hosted page where citizens see CRITICAL zones appear live                |

The alert wall is the pay-off for the Pub/Sub beat: it shows the alert reaching
someone outside the dashboard. Open it in a second tab **before** recording, so
the CRITICAL zone appears without a page reload.

## Script

| Time      | Beat                                                                                                                                                                                                                                    |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0:00–0:18 | The problem: urban heat islands, and that nobody can point at a block and say how bad it is.                                                                                                                                            |
| 0:18–0:32 | Upload the industrial district aerial crop.                                                                                                                                                                                             |
| 0:32–0:52 | Run the analysis. Narrate over the wait: Gemini 2.5 Flash reading surface materials, NOAA climate telemetry from BigQuery.                                                                                                              |
| 0:52–1:25 | The result: **HVI 8.1 CRITICAL**. The Pub/Sub alert banner confirms a real alert was published.                                                                                                                                         |
| 1:25–1:45 | Cut to the public alert wall. The zone is already there — the alert left the system and reached citizens.                                                                                                                               |
| 1:45–2:08 | The passive cooling blueprint: wind corridor orientation, retroreflective coating area in m², projected temperature drop.                                                                                                               |
| 2:08–2:45 | Type `Botanic` into the search beside the map and pick the suggestion. A **coordinate**, no upload, real Google satellite imagery. **HVI 1.5 LOW**, "Dense Tropical Forest". Same pipeline, same model — the score tracks real surfaces. |
| 2:45–2:58 | Scroll to the city map: every analysed zone on one map, coloured by risk.                                                                                                                                                                |
| 2:58–3:15 | Architecture close: Gemini 2.5 Flash, Maps Static/Geocoding/Places, BigQuery NOAA GSOD, Firestore, Pub/Sub, Firebase Hosting, all on Cloud Run in `asia-southeast1`.                                                                     |

If this runs long, cut the city map beat. Do not cut the alert wall — it is what
proves the alert is real rather than a banner.

## Scripted scenarios

| Scenario        | Input                           | Expected                           |
| --------------- | ------------------------------- | ---------------------------------- |
| Critical opener | upload `industrial_hotspot.jpg` | HVI 8.1 CRITICAL, alert dispatched |
| Low contrast    | coordinate 1.3521, 103.8198     | HVI 1.5 LOW, no alert              |

Each reproduced identically on three consecutive runs on 2026-10-05. They are
inferred by the model, not hardcoded, so treat them as highly likely rather than
guaranteed. Generate the sample with `python backend/seed_samples.py` if
`data_samples/` is empty — it is not committed.

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

Restore normal autoscaling, since `--max-instances=1` is a demo-time setting and
not a production one:

```bash
gcloud run services update hotspot-backend --region asia-southeast1 --max-instances=3
```
