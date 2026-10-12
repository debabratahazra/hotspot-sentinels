"""Fill the AI Builder Cup submission template from verified project facts.

Writes a NEW file and never modifies the prescribed template, so the original
stays pristine (the rules threaten disqualification for format deviation).
Run with:  uv run --with python-pptx --no-project python tools/fill_submission_deck.py
"""

from pathlib import Path

from pptx import Presentation
from pptx.util import Pt

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "Submission Template _ AI Builder Cup.pptx"
OUTPUT = ROOT / "HotSpot_Sentinels_Submission.pptx"

BACKEND = "https://hotspot-backend-153692178986.asia-southeast1.run.app"
FRONTEND = "https://hotspot-frontend-153692178986.asia-southeast1.run.app"
REPO = "https://github.com/debabratahazra/hotspot-sentinels"

# Keyed by slide number. Each entry is a list of (text, level, bold) paragraphs.
# Anything only the team can supply is left as an explicit [BRACKETED] placeholder
# so it is obvious on screen rather than quietly missing.
CONTENT: dict[int, list[tuple[str, int, bool]]] = {
    1: [
        ("Team name: [FILL IN]", 0, False),
        ("Team leader name: [FILL IN]", 0, False),
        ("Problem Statement: Sustainability and Social Impact — urban heat islands", 0, False),
    ],
    3: [
        ("HotSpot Sentinels turns ordinary aerial or satellite imagery into an actionable "
         "urban-heat retrofit plan.", 0, True),
        ("Upload a district image, or simply name a coordinate. The system returns:", 0, False),
        ("A 0–10 Heat Vulnerability Index (HVI) with a risk band", 1, False),
        ("The surface-material breakdown driving that score — asphalt, dark roof, concrete, canopy", 1, False),
        ("A passive-cooling blueprint: wind-corridor orientation, retroreflective coating area in m², "
         "and projected surface temperature drop in °C", 1, False),
        ("When a zone scores CRITICAL, an alert is published automatically so the right team hears "
         "about it without anyone watching a dashboard.", 0, False),
    ],
    4: [
        ("How it differs from existing ideas", 0, True),
        ("Most heat-island tools stop at a map that shows where it is hot. This one explains why — "
         "which surfaces cause it — and prescribes what to change, with quantities.", 1, False),
        ("No specialist thermal or LiDAR capture needed. It reads ordinary RGB imagery, so any city "
         "with satellite coverage can use it today.", 1, False),
        ("How it solves the problem", 0, True),
        ("Planners get a costed, specific intervention per zone instead of a heat map they must "
         "interpret themselves.", 1, False),
        ("Measured surface temperature is grounded in live NOAA climate telemetry, not assumed.", 1, False),
        ("USP", 0, True),
        ("Image in, retrofit plan out, in about 15 seconds — with a machine-readable contract so the "
         "output can feed procurement or GIS systems directly.", 1, False),
    ],
    5: [
        ("Dual input: upload an aerial image, or analyse any coordinate from live satellite imagery", 0, False),
        ("0–10 Heat Vulnerability Index with LOW / MODERATE / HIGH / CRITICAL banding", 0, False),
        ("Surface-material breakdown that always totals 100%", 0, False),
        ("Passive-cooling blueprint with metric quantities — m², °C, corridor orientation", 0, False),
        ("Live ambient temperature from the NOAA GSOD public dataset, with an offline fallback", 0, False),
        ("Automatic Pub/Sub alert the moment a zone is CRITICAL", 0, False),
        ("Persistent scan history, queryable through the API", 0, False),
        ("Health endpoint reporting every dependency independently", 0, False),
        ("Graceful degradation: a failed alert or climate lookup never fails the analysis", 0, False),
    ],
    6: [
        ("[INSERT DIAGRAM — described below]", 0, True),
        ("1. Operator uploads an image or selects a coordinate in the Streamlit dashboard", 0, False),
        ("2. Dashboard POSTs to /api/analyze on the FastAPI service (Cloud Run)", 0, False),
        ("3. For a coordinate, the backend fetches attributed satellite imagery from the Maps Static API "
         "and shares it via Cloud Storage so any instance can serve it", 0, False),
        ("4. BigQuery returns live NOAA GSOD ambient temperature for the location", 0, False),
        ("5. Gemini 2.5 Flash reads the imagery and returns a schema-constrained JSON report", 0, False),
        ("6. The report is persisted to Firestore", 0, False),
        ("7. If risk is CRITICAL, an alert is published to Pub/Sub", 0, False),
        ("8. The dashboard renders the HVI gauge, surface chart and cooling blueprint", 0, False),
    ],
    8: [
        ("[INSERT DIAGRAM — components below]", 0, True),
        ("Frontend — Streamlit on Cloud Run (asia-southeast1), its own container", 0, False),
        ("Backend — FastAPI on Cloud Run, the only HTTP layer; async orchestration", 0, False),
        ("AI — Gemini 2.5 Flash via the google-genai SDK, structured JSON response schema", 0, False),
        ("Data — Firestore (scan records) · BigQuery (NOAA GSOD) · Cloud Storage (shared imagery cache)", 0, False),
        ("Messaging — Pub/Sub topic for CRITICAL alerts", 0, False),
        ("Secrets — Secret Manager; the Maps key is mounted, never an environment variable", 0, False),
        ("Identity — one runtime service account with six narrow roles and zero key files", 0, False),
        ("Delivery — GitHub Actions; a version tag deploys both services via Workload Identity Federation", 0, False),
    ],
    9: [
        ("Google Cloud", 0, True),
        ("Gemini 2.5 Flash (Vertex AI) — multimodal analysis with enforced JSON schema", 1, False),
        ("Cloud Run — both services, containerised, scale to zero, asia-southeast1", 1, False),
        ("Firestore — Firebase's document database, Native mode; system of record for every scan", 1, False),
        ("BigQuery — NOAA GSOD public dataset for live ambient temperature", 1, False),
        ("Pub/Sub — critical-zone alert fan-out", 1, False),
        ("Cloud Storage — imagery cache shared across instances", 1, False),
        ("Secret Manager · Artifact Registry · Maps Static API", 1, False),
        ("Application", 0, True),
        ("Python 3.10+ · FastAPI · Streamlit · Pydantic · Docker (multi-stage, non-root)", 1, False),
        ("GitHub Actions CI/CD with Workload Identity Federation — no service-account keys", 1, False),
    ],
    11: [
        ("[INSERT SCREENSHOTS]", 0, True),
        ("Suggested captures from the live dashboard:", 0, False),
        ("1. Dashboard landing view with the analysis controls", 1, False),
        ("2. A CRITICAL result — HVI gauge, risk badge and the Pub/Sub alert banner", 1, False),
        ("3. The surface-material breakdown chart", 1, False),
        ("4. The passive-cooling blueprint with metric quantities", 1, False),
        ("5. The LOW-risk contrast result for comparison", 1, False),
        (f"Live dashboard: {FRONTEND}", 0, False),
    ],
    12: [
        ("Measured against the deployed stack, not estimated", 0, True),
        ("Analysis latency — 15.6 s for an uploaded image; 13.5 s for a coordinate "
         "(coordinate also fetches and renders satellite imagery)", 0, False),
        ("Representative results — industrial district: HVI 8.1 CRITICAL, alert published. "
         "Botanic Gardens: HVI 1.5 LOW, no alert. Same pipeline, same model.", 0, False),
        ("Climate grounding — live NOAA GSOD telemetry at 31.0 °C via BigQuery", 0, False),
        ("Quality — 686 automated tests, all offline; 98.2% backend coverage with no file below a "
         "70% floor; 0 open P0 defects", 0, False),
        ("Reliability — /api/health reports gemini, firestore, pubsub and bigquery independently; "
         "all four ready in production", 0, False),
        ("Security — no service-account key files; the Maps API key is mounted from Secret Manager, "
         "never exposed as an environment variable; gitleaks scans every push", 0, False),
        ("Delivery — five required CI checks gate every merge; a version tag deploys both services "
         "keylessly and verifies each one separately", 0, False),
    ],
    13: [
        ("Known limitations, stated plainly", 0, True),
        ("A scan does not yet store the object URI of the exact image it analysed; durable imagery "
         "storage exists, the record linkage does not.", 1, False),
        ("HVI is model-inferred, so scores vary slightly between runs rather than being deterministic.", 1, False),
        ("Future development", 0, True),
        ("Time-series tracking per zone to measure whether an intervention actually worked", 1, False),
        ("Batch analysis across a whole city grid, ranked by intervention impact per dollar", 1, False),
        ("Cost modelling attached to the cooling blueprint for direct procurement use", 1, False),
        ("Dashboards for citizens, not just planners, to surface neighbourhood-level risk", 1, False),
    ],
    14: [
        ("GitHub Public Repository", 0, True),
        (REPO, 1, False),
        ("Demo Video Link", 0, True),
        ("[INSERT VIDEO URL — 3 to 4 minutes, publicly accessible]", 1, False),
        ("Final Product Link (deployed prototype)", 0, True),
        (FRONTEND, 1, False),
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
                suffix = " [FILL IN]"
            elif label.startswith("Team leader name:"):
                suffix = " [FILL IN]"
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


def main() -> None:
    deck = Presentation(str(TEMPLATE))
    slides = list(deck.slides)
    print(f"  slide  1: {'filled' if fill_team_slide(slides[0]) else 'FAILED'} (team details)")
    for number, paragraphs in CONTENT.items():
        if number == 1:
            continue
        slide = slides[number - 1]
        # Denser slides get smaller type so nothing overflows the template's box.
        size = 11 if len(paragraphs) > 8 else 13
        ok = fill(slide, paragraphs, size)
        print(f"  slide {number:>2}: {'filled' if ok else 'NO BODY SHAPE FOUND'} ({len(paragraphs)} paragraphs)")
    deck.save(str(OUTPUT))
    print(f"\nwrote {OUTPUT.name}")
    print(f"template untouched: {TEMPLATE.name}")


if __name__ == "__main__":
    main()
