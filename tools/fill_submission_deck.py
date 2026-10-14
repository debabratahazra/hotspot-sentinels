"""Fill the AI Builder Cup submission template from verified project facts.

Writes a NEW file and never modifies the prescribed template, so the original
stays pristine (the rules threaten disqualification for format deviation).
Run with:  uv run --with python-pptx --no-project python tools/fill_submission_deck.py
"""

from pathlib import Path

from pptx import Presentation
from pptx.util import Emu, Pt

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "Submission Template _ AI Builder Cup.pptx"
OUTPUT = ROOT / "HotSpot_Sentinels_Submission.pptx"
ASSETS = ROOT / "docs" / "deck-assets"

TEAM_NAME = "HotSpot Sentinels"
TEAM_LEADER = "Debabrata Hazra"
TEAM_MEMBERS = "Debabrata Hazra, Deepthi Konda"

BACKEND = "https://hotspot-backend-153692178986.asia-southeast1.run.app"
FRONTEND = "https://hotspot-frontend-153692178986.asia-southeast1.run.app"
ALERT_WALL = "https://hotspot-sentinels-7364.web.app"
REPO = "https://github.com/debabratahazra/hotspot-sentinels"

# Slides that carry a picture instead of a wall of text.
IMAGES: dict[int, tuple[str, str]] = {
    6: ("diagram-process-flow.png",
        "Operator to retrofit plan. Steps 3-6 are independent: a failed alert or "
        "climate lookup degrades the report, it never fails the analysis."),
    8: ("diagram-architecture.png",
        "Two containers on Cloud Run in asia-southeast1. The Maps key is mounted from "
        "Secret Manager and proxied by the backend, so it never reaches a browser."),
    11: ("montage-prototype.png",
         "Live analysis of Pasir Panjang Terminal, Singapore, from Google satellite "
         "imagery: HVI 8.6 CRITICAL, 0% tree canopy, ambient 31.0 °C measured from NOAA "
         "GSOD, and the Pub/Sub alert already visible to citizens on the public wall."),
}

# Keyed by slide number. Each entry is a list of (text, level, bold) paragraphs.
CONTENT: dict[int, list[tuple[str, int, bool]]] = {
    3: [
        ("Heat is the deadliest weather there is, and cities make it worse. Dark roofs and "
         "asphalt turn a neighbourhood into an oven several degrees hotter than the land "
         "around it.", 0, True),
        ("That heat kills the elderly and the outdoor poor, pushes street animals and urban "
         "wildlife out of their range, and forces air-conditioning demand that burns more "
         "carbon — which makes the next summer hotter still.", 0, False),
        ("The barrier is not willingness. It is that nobody can point at one city block and "
         "say how bad this one is, and what exactly to do about it.", 0, False),
        ("HotSpot Sentinels answers both in about fifteen seconds:", 0, True),
        ("A 0–10 Heat Vulnerability Index with a risk band", 1, False),
        ("The surface materials driving that score — asphalt, dark roof, concrete, canopy", 1, False),
        ("A passive-cooling blueprint with quantities: corridor orientation, retroreflective "
         "coating in m², projected temperature drop in °C", 1, False),
        ("When a zone scores CRITICAL it publishes a public alert automatically, so residents "
         "learn their street is dangerous without needing access to a planning dashboard.", 0, False),
    ],
    4: [
        ("Why this matters — environment, people, animals", 0, True),
        ("Measured on the live system: a container terminal at 0% tree canopy scores 8.6 CRITICAL; "
         "a national park at 100% canopy scores 1.5 LOW. Same model, same pipeline. That gap is "
         "exactly what tree cover and reflective surfaces buy a city.", 1, False),
        ("The blueprint for one CRITICAL zone projects an 8–10 °C surface temperature drop — the "
         "difference between a heatwave that is survivable and one that is not, and a direct cut "
         "in cooling energy demand.", 1, False),
        ("Cooler blocks mean habitable shade for street animals and urban wildlife, not only "
         "comfort for people indoors.", 1, False),
        ("How it differs from existing ideas", 0, True),
        ("Most heat-island tools stop at a map showing where it is hot. This explains why — which "
         "surfaces cause it — and prescribes what to change, with quantities.", 1, False),
        ("No thermal or LiDAR capture needed. It reads ordinary RGB imagery, so any city with "
         "satellite coverage can start today, including ones that cannot fund a survey.", 1, False),
        ("USP", 0, True),
        ("Image or place name in, costed retrofit plan out, in about fifteen seconds — with a "
         "machine-readable contract that can feed procurement or GIS directly.", 1, False),
    ],
    5: [
        ("Analyse anywhere — four ways to choose a location", 0, True),
        ("A shortcut list of 15 places across Asia, ordered most built-up to most green, so the "
         "list itself runs from CRITICAL down to LOW", 1, False),
        ("Type three characters and pick from live Google Places suggestions, down to "
         "neighbourhood level; click any point on a world map; or paste coordinates", 1, False),
        ("A clicked point is named automatically — city and country on land, or the sea or "
         "ocean at sea", 1, False),
        ("Whichever method is used, both search boxes and the coordinate fields update "
         "together, so the screen never names one place while analysing another", 1, False),
        ("Analysis", 0, True),
        ("Upload an aerial image, or analyse a coordinate from live Google satellite imagery", 1, False),
        ("0–10 Heat Vulnerability Index with LOW / MODERATE / HIGH / CRITICAL banding", 1, False),
        ("Surface-material breakdown that always totals 100%", 1, False),
        ("Passive-cooling blueprint in metric units — m², °C, corridor orientation", 1, False),
        ("Live ambient temperature from NOAA GSOD via BigQuery, with an offline fallback", 1, False),
        ("Reaching people", 0, True),
        ("Automatic Pub/Sub alert the moment a zone is CRITICAL", 1, False),
        ("Public alert wall on Firebase Hosting — citizens see critical zones appear live, while "
         "operator scan data stays private", 1, False),
        ("City-wide map of every analysed zone coloured by risk: a retrofit queue ordered worst-first", 1, False),
        ("Trustworthiness", 0, True),
        ("Every identity field is labelled supplied or inferred, so a planner knows which numbers "
         "the model guessed", 1, False),
        ("Graceful degradation: a failed alert or climate lookup never fails the analysis", 1, False),
    ],
    9: [
        ("Google Cloud", 0, True),
        ("Gemini 2.5 Flash (Vertex AI) — multimodal analysis with an enforced JSON schema", 1, False),
        ("Cloud Run — both services, containerised, scale to zero, asia-southeast1", 1, False),
        ("Firebase — Firestore as the system of record, Hosting for the public alert wall, and "
         "security rules making curated alerts world-readable but never writable", 1, False),
        ("BigQuery — NOAA GSOD public dataset for live ambient temperature", 1, False),
        ("Pub/Sub — critical-zone alert fan-out", 1, False),
        ("Cloud Storage — imagery cache shared across instances", 1, False),
        ("Maps Static, Geocoding and Places APIs — imagery, place search and reverse naming, all "
         "proxied server-side", 1, False),
        ("Secret Manager · Artifact Registry · Cloud Build", 1, False),
        ("Application", 0, True),
        ("Python 3.10+ · FastAPI · Streamlit · Pydantic · Docker (multi-stage, non-root)", 1, False),
        ("GitHub Actions CI/CD with Workload Identity Federation — no service-account keys exist", 1, False),
    ],
    12: [
        ("Measured against the deployed stack on 2026-10-14, not estimated", 0, True),
        ("Latency — 21.6 s for the container-terminal coordinate, 12.6 s for the park, 17.2 s for "
         "an uploaded image. Coordinates also fetch and render satellite imagery. Cold start "
         "is now close to warm.", 0, False),
        ("Representative results, each reproduced on three consecutive runs:", 0, False),
        ("Pasir Panjang Terminal, Singapore — HVI 8.6 CRITICAL, 0% canopy, alert published", 1, False),
        ("Old Dhaka — HVI 8.5 CRITICAL, 0% canopy · Kolkata — 8.2 · Manila — 8.1", 1, False),
        ("Singapore Botanic Gardens — HVI 1.5 LOW, 100% canopy, no alert", 1, False),
        ("Climate grounding — live NOAA GSOD telemetry at 31.0 °C via BigQuery", 0, False),
        ("Quality — 815 automated tests, all offline; 96% backend coverage with no file below a "
         "70% floor; 0 open P0 defects", 0, False),
        ("Reliability — /api/health reports gemini, firestore, pubsub and bigquery independently; "
         "all four ready in production", 0, False),
        ("Safety — uploads that are not JPEG or PNG are rejected 415, including files disguised "
         "with an image content type; oversized uploads are rejected 413 before any model spend", 0, False),
        ("Security — no service-account key files anywhere; the Maps key is mounted from Secret "
         "Manager, never an environment variable; gitleaks scans every push", 0, False),
        ("Delivery — five required CI checks gate every merge; a version tag deploys both services "
         "keylessly and verifies each separately", 0, False),
    ],
    13: [
        ("Engineering challenges met", 0, True),
        ("A generative model will not reliably return parseable JSON on its own. The analyser pins "
         "a response schema and the backend refuses a non-conforming payload rather than showing a "
         "malformed report.", 1, False),
        ("Cloud Run scales to zero, so an in-process imagery cache died with the container. Moving "
         "it to Cloud Storage made imagery survive scale-to-zero and be shared across instances.", 1, False),
        ("A map click could not write the coordinate inputs, because Streamlit forbids writing a "
         "widget key after that widget exists. The click is deferred and applied on the next run, "
         "before any widget is created.", 1, False),
        ("Google answers 200 with a Plus Code and no country over open water, not ZERO_RESULTS. "
         "That absent country became the signal for naming a point at sea.", 1, False),
        ("Known limitations, stated plainly", 0, True),
        ("The model has no concept of water. Pointed at open sea it reads the dark surface "
         "as asphalt and scores it CRITICAL. Found by fetching the imagery for a shipping "
         "lane and looking at it; the shipped presets are now all verified land, but a user "
         "can still click the ocean. A water check is the next thing to build.", 1, False),
        ("HVI is model-inferred, so scores vary slightly between runs. It is a triage tool that "
         "says where to survey first; it does not replace the survey.", 1, False),
        ("Given an image with no location metadata the model guesses coordinates, and can guess "
         "wrong. The report labels those fields inferred rather than presenting them as fact.", 1, False),
        ("A scan does not yet store the object URI of the exact image it analysed.", 1, False),
        ("Future development", 0, True),
        ("Time-series tracking per zone, to measure whether an intervention actually worked", 1, False),
        ("Batch analysis across a whole city grid, ranked by cooling impact per dollar", 1, False),
        ("Cost modelling attached to the blueprint for direct procurement use", 1, False),
        ("Local-language citizen alerts, and routing to heat shelters during a heatwave", 1, False),
    ],
    14: [
        ("GitHub Public Repository", 0, True),
        (REPO, 1, False),
        ("Demo Video Link", 0, True),
        ("[INSERT VIDEO URL — 3 to 4 minutes, publicly accessible]", 1, False),
        ("Final Product Link (deployed prototype)", 0, True),
        (FRONTEND, 1, False),
        ("Public alert wall (live, no sign-in)", 0, True),
        (ALERT_WALL, 1, False),
        ("Backend API (health check)", 0, True),
        (f"{BACKEND}/api/health", 1, False),
    ],
}


def body_shape(slide):
    """The template's content area: the one empty text frame that is not the title."""
    candidates = [s for s in slide.shapes if s.has_text_frame and not s.text_frame.text.strip()]
    return max(candidates, key=lambda s: s.width * s.height) if candidates else None


def fill_team_slide(slide) -> bool:
    """Slide 1 ships with its labels already present, so extend them in place."""
    for shape in slide.shapes:
        if not shape.has_text_frame or "Team name" not in shape.text_frame.text:
            continue
        for para in shape.text_frame.paragraphs:
            label = para.text.strip()
            if label.startswith("Team name:"):
                suffix = f" {TEAM_NAME}"
            elif label.startswith("Team leader name:"):
                suffix = f" {TEAM_LEADER}   |   Team members: {TEAM_MEMBERS}"
            elif label.startswith("Problem Statement:"):
                suffix = " Sustainability and Social Impact — urban heat islands"
            else:
                continue
            if para.runs:
                para.runs[-1].text = para.runs[-1].text.rstrip() + suffix
            else:
                para.text = label + suffix
        return True
    return False


def fill(slide, paragraphs, size_pt):
    shape = body_shape(slide)
    if shape is None:
        return False
    tf = shape.text_frame
    tf.word_wrap = True
    for index, (text, level, bold) in enumerate(paragraphs):
        para = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        para.text = text
        para.level = level
        for run in para.runs:
            run.font.size = Pt(size_pt)
            run.font.bold = bold
    return True


def fill_with_image(slide, filename, caption) -> bool:
    """Put a picture in the body area, captioned, scaled so it is never distorted."""
    from PIL import Image

    shape = body_shape(slide)
    if shape is None:
        return False
    source = ASSETS / filename
    if not source.exists():
        fill(slide, [(f"[MISSING ASSET: {filename}]", 0, True)], 14)
        return False

    left, top, width, height = shape.left, shape.top, shape.width, shape.height
    caption_height = Emu(int(height * 0.18))
    frame_height = height - caption_height

    native_width, native_height = Image.open(source).size
    scale = min(width / native_width, frame_height / native_height)
    draw_width, draw_height = int(native_width * scale), int(native_height * scale)

    slide.shapes.add_picture(
        str(source),
        left + int((width - draw_width) / 2),
        top + int((frame_height - draw_height) / 2),
        width=draw_width, height=draw_height,
    )

    shape.top = top + frame_height
    shape.height = caption_height
    tf = shape.text_frame
    tf.word_wrap = True
    para = tf.paragraphs[0]
    para.text = caption
    for run in para.runs:
        run.font.size = Pt(11)
    return True


def main() -> None:
    deck = Presentation(str(TEMPLATE))
    slides = list(deck.slides)
    print(f"  slide  1: {'filled' if fill_team_slide(slides[0]) else 'FAILED'} (team details)")

    for number in sorted(set(CONTENT) | set(IMAGES)):
        slide = slides[number - 1]
        if number in IMAGES:
            filename, caption = IMAGES[number]
            ok = fill_with_image(slide, filename, caption)
            print(f"  slide {number:>2}: {'image ' if ok else 'FAILED'} ({filename})")
            continue
        paragraphs = CONTENT[number]
        # Denser slides get smaller type so nothing overflows the template's box.
        size = 11 if len(paragraphs) > 8 else 13
        ok = fill(slide, paragraphs, size)
        print(f"  slide {number:>2}: {'filled' if ok else 'NO BODY SHAPE FOUND'} "
              f"({len(paragraphs)} paragraphs)")

    deck.save(str(OUTPUT))
    print(f"\nwrote {OUTPUT.name} ({OUTPUT.stat().st_size // 1024} KB)")
    print(f"template untouched: {TEMPLATE.name}")


if __name__ == "__main__":
    main()
