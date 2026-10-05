# Demo Runbook

A 3-minute recording of HotSpot Sentinels against the deployed stack. Every number
below was measured on 2026-10-04, not estimated.

|               |                                                               |
| ------------- | ------------------------------------------------------------- |
| Dashboard     | https://hotspot-frontend-153692178986.asia-southeast1.run.app |
| Backend       | https://hotspot-backend-153692178986.asia-southeast1.run.app  |
| Region        | `asia-southeast1`                                             |
| Recording cap | **3 minutes** (OQ-4)                                          |

## The one thing that will break the demo

The imagery cache is **in-process**. Cloud Run scales to zero when idle, the
container dies, and the cache dies with it. A coordinate warmed an hour ago is
cold again, and a cold `/api/imagery` returns 502 — which the dashboard correctly
renders as "Required Google Maps attribution image is unavailable", immediately
after a perfectly successful analysis.

This was observed: both demo coordinates returned 502 roughly two hours after
being warmed, with `maxScale=1` already set.

**Warm the cache immediately before recording and do not leave a long idle gap.**

Since 2026-10-05 this affects only the **contrast beat**. The opener is an upload,
which never calls the Maps API, so the demo's CRITICAL result and alert cannot be
taken out by a cold cache.

## Pre-flight

Run this within a few minutes of recording. It pins a single instance, warms the
contrast coordinate, and proves the imagery is being served.

```bash
U=https://hotspot-backend-153692178986.asia-southeast1.run.app

# One instance only: the cache is per-process, so a second instance would serve
# /api/imagery without the image the analysis just fetched.
gcloud run services update hotspot-backend --region asia-southeast1 --max-instances=1

# Generate the sample if data_samples/ is empty; it is not committed.
python backend/seed_samples.py

# Throwaway call to absorb the container cold start (36 s cold vs 15 s warm).
curl -sS -o /dev/null -X POST "$U/api/analyze" -F file=@data_samples/industrial_hotspot.jpg

# Warm the contrast coordinate.
curl -sS -o /dev/null -X POST "$U/api/analyze" -F imagery_lat=1.3521 -F imagery_lng=103.8198

# Must print 200. A 502 means the cache is cold — rerun the call above.
curl -sS -o /dev/null -w 'botanic gardens %{http_code}\n' "$U/api/imagery?lat=1.3521&lng=103.8198"

# All four dependencies must read "ready".
curl -sS "$U/api/health"
```

After recording, restore autoscaling — `--max-instances=1` is a demo constraint,
not a production setting:

```bash
gcloud run services update hotspot-backend --region asia-southeast1 --max-instances=3
```

## Measured timings

Re-measured against the deployed stack on 2026-10-05. **The opener changed** — see
"The port terminal no longer reaches CRITICAL" below.

| Step                                   | API only | Notes                         |
| -------------------------------------- | -------- | ----------------------------- |
| Opening analysis (industrial upload)   | **15.0 s** | 3 runs: 15.0 / 14.9 / 15.9 s |
| Contrast analysis (Botanic Gardens)    | **13.4 s** | unchanged from 2026-10-04     |
| **Total spent waiting**                | **~28 s** |                               |

That leaves roughly **150 seconds of the 180-second budget** for narration — about
12 seconds more headroom than the previous coordinate-led opener. Add a few seconds
for UI rendering on top of the API figures. Either narrate over the spinner or cut
the wait in the edit; do not record it in silence.

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

The sidebar collapses once a result renders. To switch from the opener to the
contrast location you must reopen it with the `»` control at the top left before
the Location shortcut is reachable. Rehearse that movement; it is easy to fumble
on camera.

## Script

| Time      | Beat                                                                                                                                                                       |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0:00–0:20 | The problem: urban heat islands, and that nobody can point at a block and say how bad it is.                                                                               |
| 0:20–0:35 | Upload the industrial district aerial crop.                                                                                                                                |
| 0:35–0:55 | Run the analysis. Narrate over the wait: Gemini 2.5 Flash reading surface materials, NOAA climate telemetry from BigQuery.                                                 |
| 0:55–1:40 | The result: **HVI 8.1 CRITICAL**. The Pub/Sub alert banner confirms a real alert was published.                                                                            |
| 1:40–2:05 | The passive cooling blueprint: wind corridor orientation, retroreflective coating area in m², projected temperature drop.                                                  |
| 2:05–2:40 | Reopen the sidebar with `»`, switch to Botanic Gardens — a **coordinate**, no upload, real Google satellite imagery. **HVI 1.5 LOW**, "Dense Tropical Forest". Same pipeline, same model — the score tracks real surfaces, not a guess. |
| 2:40–3:00 | Architecture close: Gemini 2.5 Flash, Maps Static API, BigQuery NOAA GSOD, Firestore, Pub/Sub, all on Cloud Run in `asia-southeast1`.                                      |

## Scripted scenarios

| Scenario        | Input                            | Expected                           |
| --------------- | -------------------------------- | ---------------------------------- |
| Critical opener | upload `industrial_hotspot.jpg`  | HVI 8.1 CRITICAL, alert dispatched |
| Low contrast    | coordinate 1.3521, 103.8198      | HVI 1.5 LOW, no alert              |

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
