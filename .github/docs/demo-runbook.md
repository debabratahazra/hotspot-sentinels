# Demo Runbook

A 3-minute recording of HotSpot Sentinels against the deployed stack. Every number
below was measured on 2026-10-04, not estimated.

| | |
| --- | --- |
| Dashboard | https://hotspot-frontend-153692178986.asia-southeast1.run.app |
| Backend | https://hotspot-backend-153692178986.asia-southeast1.run.app |
| Region | `asia-southeast1` |
| Recording cap | **3 minutes** (OQ-4) |

## The one thing that will break the demo

The imagery cache is **in-process**. Cloud Run scales to zero when idle, the
container dies, and the cache dies with it. A coordinate warmed an hour ago is
cold again, and a cold `/api/imagery` returns 502 — which the dashboard correctly
renders as "Required Google Maps attribution image is unavailable", immediately
after a perfectly successful analysis.

This was observed: both demo coordinates returned 502 roughly two hours after
being warmed, with `maxScale=1` already set.

**Warm the cache immediately before recording and do not leave a long idle gap.**

## Pre-flight

Run this within a few minutes of recording. It pins a single instance, warms both
coordinates, and proves the imagery is being served.

```bash
U=https://hotspot-backend-153692178986.asia-southeast1.run.app

# One instance only: the cache is per-process, so a second instance would serve
# /api/imagery without the image the analysis just fetched.
gcloud run services update hotspot-backend --region asia-southeast1 --max-instances=1

# Warm both demo coordinates.
curl -sS -o /dev/null -X POST "$U/api/analyze" -F imagery_lat=1.2897 -F imagery_lng=103.7540
curl -sS -o /dev/null -X POST "$U/api/analyze" -F imagery_lat=1.3521 -F imagery_lng=103.8198

# Both must print 200. A 502 means the cache is cold — rerun the two calls above.
curl -sS -o /dev/null -w 'port terminal   %{http_code}\n' "$U/api/imagery?lat=1.2897&lng=103.754"
curl -sS -o /dev/null -w 'botanic gardens %{http_code}\n' "$U/api/imagery?lat=1.3521&lng=103.8198"

# All four dependencies must read "ready".
curl -sS "$U/api/health"
```

Then load the dashboard once and confirm it opens on **Singapore Port Terminal**
with latitude `1.2897` and longitude `103.754`.

## Measured timings

Rehearsed end to end through the deployed dashboard on 2026-10-04.

| Step | Through the UI | API only |
| --- | --- | --- |
| Opening analysis (Port Terminal) | **25.7 s** | 23.7 s |
| Contrast analysis (Botanic Gardens) | **12.5 s** | 13.4 s |
| **Total spent waiting** | **38.2 s** | |

That leaves about **142 seconds of the 180-second budget** for narration, which
the script below fits. The UI is slower than the API alone because it also fetches
and renders the attributed image. Either narrate over the spinner or cut the wait
in the edit — do not record it in silence.

The first analysis after an idle period is the slow one: it pays a container cold
start and a Maps fetch. Run one throwaway analysis before recording.

## Flow gotcha

The sidebar collapses once a result renders. To switch from the opener to the
contrast location you must reopen it with the `»` control at the top left before
the Location shortcut is reachable. Rehearse that movement; it is easy to fumble
on camera.

## Script

| Time | Beat |
| --- | --- |
| 0:00–0:20 | The problem: urban heat islands, and that nobody can point at a block and say how bad it is. |
| 0:20–0:35 | The dashboard opens on Singapore's port terminal. One click, no upload. |
| 0:35–1:00 | Run the analysis. Narrate over the wait: real Google satellite imagery, Gemini 2.5 Flash reading surface materials, NOAA climate telemetry from BigQuery. |
| 1:00–1:45 | The result: **HVI 8.7 CRITICAL**, 100% asphalt, zero canopy, 31 °C measured. The Pub/Sub alert banner confirms a real alert was published. |
| 1:45–2:10 | The passive cooling blueprint: wind corridor orientation, retroreflective coating area in m², projected temperature drop. |
| 2:10–2:40 | Reopen the sidebar with `»`, switch to Botanic Gardens. **HVI 1.5 LOW**, "Dense Tropical Forest". Same pipeline, same model — the score tracks real surfaces, not a guess. |
| 2:40–3:00 | Architecture close: Gemini 2.5 Flash, Maps Static API, BigQuery NOAA GSOD, Firestore, Pub/Sub, all on Cloud Run in `asia-southeast1`. |

## Scripted scenarios

| Scenario | Coordinates | Expected |
| --- | --- | --- |
| Critical opener | 1.2897, 103.7540 | HVI 8.7 CRITICAL, alert dispatched |
| Low contrast | 1.3521, 103.8198 | HVI 1.5 LOW, no alert |

Both have reproduced identically on three separate runs. They are inferred by the
model, not hardcoded, so treat them as highly likely rather than guaranteed.

## Fallbacks

| If this happens | Do this |
| --- | --- |
| Imagery missing, "attribution image unavailable" | Cache went cold. Rerun the two warm-up calls, reload, re-record that take. |
| Analysis exceeds ~30 s | Cold start. Run one throwaway analysis first, then record. |
| `/api/health` reports `degraded` | Read which dependency is down. Analysis still works if `gemini` is ready; climate falls back to 38.5 °C and the UI labels it as a fallback. |
| Coordinate returns 502 | That coordinate has no cached image. Use the other scenario and warm the failing one again. |
| Analysis returns 502 | The model occasionally returns a payload that fails schema validation; one run in four did so on 2026-10-04. The backend correctly refuses it rather than showing a malformed report. Simply run it again — two immediate retries both succeeded. Do a throwaway run before recording so a retry is not your opening shot. |
| Score differs from the table | Not a failure — the model re-reads the image. Narrate the score actually shown; the band is what matters. |
| Dashboard unreachable | Check the frontend revision is serving: `gcloud run services describe hotspot-frontend --region asia-southeast1`. |

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
