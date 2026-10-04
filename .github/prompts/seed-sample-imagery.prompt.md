---
name: "Seed Sample Imagery"
description: "Scaffold backend/tools/seed_samples.py: generates three synthetic aerial test images with PIL, writes them to data_samples/, and uploads them to the GCS bucket."
argument-hint: "Optional: extra scene types or image resolution"
agent: "agent"
tools: ["edit", "search", "runCommands", "problems"]
---

Build the mock satellite asset seeder for HotSpot Sentinels (Epic 1 / Story 1.2).

Project rules: [COPILOT_GUIDE.md](../../COPILOT_GUIDE.md).

## Target file

`backend/tools/seed_samples.py`

## What to generate

Three programmatic RGB images (Pillow, 1024x1024 unless told otherwise), drawn with primitives so no external assets are needed:

1. `industrial_asphalt.png` — dense dark asphalt lots, large flat dark roofs, near-zero vegetation.
2. `mixed_residential.png` — mid-tone rooftops, road grid, scattered green canopy patches.
3. `green_park.png` — dominant green canopy, water feature, thin light-coloured paths.

Each scene should be visually distinguishable enough that a vision model can infer different surface breakdowns.

## Implementation rules

- Save locally to `data_samples/` (create the directory if missing) and return/report the local paths.
- Upload to the bucket named by the `GCS_BUCKET_NAME` env var using `google.cloud.storage`, under a `samples/` prefix.
- If `GCS_BUCKET_NAME` is unset or the upload fails, log a clear warning and still exit successfully with local files written — the seeder must work offline.
- Expose `generate_samples() -> list[Path]` and `upload_samples(paths: list[Path]) -> list[str]`, wired together under `if __name__ == "__main__":`.
- Use `python-dotenv` to load `.env` so the script matches the env produced by [setup_gcp.sh](../../setup_gcp.sh).

## Done when

- `python backend/tools/seed_samples.py` writes three PNGs and prints their local paths plus any `gs://` URIs.
