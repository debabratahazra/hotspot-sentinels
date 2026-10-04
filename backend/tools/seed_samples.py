"""Generate three synthetic aerial scenes, with optional best-effort GCS uploads."""

import logging
import os
from pathlib import Path

from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError
from google.cloud import storage
from google.cloud.storage.exceptions import DataCorruption
from PIL import Image, ImageDraw
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)
_client: storage.Client | None = None
DATA_DIR = Path(__file__).resolve().parents[2] / "data_samples"
# DataCorruption is a resumable-upload checksum failure and subclasses nothing else here.
CLOUD_ERRORS = (GoogleAPIError, GoogleAuthError, RequestException, DataCorruption)


class _StorageClientError(RuntimeError):
    """Storage client configuration is unavailable."""


def _get_client() -> storage.Client:
    global _client
    if _client is None:
        try:
            _client = storage.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
        except OSError:
            raise _StorageClientError("Storage client configuration is unavailable.") from None
    return _client


def generate_samples() -> list[Path]:
    """Write RGB scenes to the repository's data_samples directory."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    paths = []

    industrial = Image.new("RGB", (1024, 1024), (38, 38, 42))
    draw = ImageDraw.Draw(industrial)
    for left in (48, 548):
        for top in (48, 548):
            draw.rectangle((left, top, left + 380, top + 350), fill=(70, 70, 76))
            for offset in range(35, 350, 45):
                draw.line((left + offset, top + 10, left + offset, top + 340),
                          fill=(88, 88, 94), width=3)
    for offset in range(40, 1000, 60):
        draw.line((offset, 470, offset + 25, 470), fill=(220, 210, 150), width=4)
        draw.rectangle((offset, 420, offset + 28, 448), fill=(180, 180, 185))
    draw.rectangle((940, 760, 1023, 1023), fill=(42, 115, 48))
    paths.append(DATA_DIR / "industrial_hotspot.jpg")
    industrial.save(paths[-1], "JPEG", quality=95)

    residential = Image.new("RGB", (1024, 1024), (92, 145, 72))
    draw = ImageDraw.Draw(residential)
    for position in (0, 480, 960):
        draw.rectangle((position, 0, position + 63, 1023), fill=(65, 65, 68))
        draw.rectangle((0, position, 1023, position + 63), fill=(65, 65, 68))
    for left in (90, 280, 570, 760):
        for top in (90, 280, 570, 760):
            draw.rectangle((left - 8, top - 8, left + 148, top + 158),
                           fill=(195, 190, 180))
            draw.rectangle((left, top, left + 140, top + 110), fill=(135, 119, 108))
            draw.line((left, top + 55, left + 140, top + 55),
                      fill=(100, 89, 82), width=5)
            draw.rectangle((left + 50, top + 111, left + 85, top + 165),
                           fill=(200, 197, 188))
            draw.ellipse((left + 105, top + 115, left + 175, top + 185),
                         fill=(35, 104, 48))
    paths.append(DATA_DIR / "mixed_residential.jpg")
    residential.save(paths[-1], "JPEG", quality=95)

    park = Image.new("RGB", (1024, 1024), (66, 145, 63))
    draw = ImageDraw.Draw(park)
    for left in range(30, 1000, 140):
        for top in range(30, 1000, 140):
            draw.ellipse((left, top, left + 110, top + 110), fill=(26, 100, 43))
            draw.ellipse((left + 15, top + 12, left + 80, top + 75),
                         fill=(38, 115, 48))
    draw.ellipse((610, 100, 950, 470), fill=(65, 137, 180))
    draw.line(((0, 550), (450, 550), (600, 750), (1023, 750)),
              fill=(220, 218, 195), width=18)
    paths.append(DATA_DIR / "cool_park.jpg")
    park.save(paths[-1], "JPEG", quality=95)
    return paths


def upload_samples(paths: list[Path]) -> list[str]:
    """Upload under samples/, retaining every local file on cloud failure."""
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        logger.warning("Skipped GCS uploads for %d local files: GCS_BUCKET_NAME is unset.",
                       len(paths))
        return []
    try:
        bucket = _get_client().bucket(bucket_name)
    except (*CLOUD_ERRORS, _StorageClientError) as error:
        logger.warning("Skipped GCS uploads for %d local files: storage client unavailable (%s).",
                       len(paths), type(error).__name__)
        return []
    uploaded = []
    for path in paths:
        try:
            blob = bucket.blob(f"samples/{path.name}")
            blob.upload_from_filename(str(path), content_type="image/jpeg", timeout=30)
        except CLOUD_ERRORS as error:
            logger.warning("Skipped GCS upload for %s: upload failed (%s); local file retained.",
                           path.name, type(error).__name__)
            continue
        uploaded.append(f"gs://{bucket_name}/{blob.name}")
    return uploaded


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    paths = generate_samples()
    for path in paths:
        print(f"Written: {path.relative_to(DATA_DIR.parent)}", flush=True)
    uploaded = upload_samples(paths)
    for uri in uploaded:
        print(f"Uploaded: {uri}")
    print(f"Summary: {len(paths)} written, {len(uploaded)} uploaded, "
          f"{len(paths) - len(uploaded)} uploads skipped.")


if __name__ == "__main__":
    main()
