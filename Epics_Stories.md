
---

#### Epic 1: Multimodal Perception & Gemini Reasoning Engine
*Goal:* Build the core inference module that passes urban satellite images to Gemini 2.5 Flash and returns structured JSON surface diagnostics and passive cooling plans[span_0](start_span)[span_0](end_span).

##### Story 1.1: Vision Inference Module
*   **File:** `backend/services/vision_analyzer.py`
*   **Prompt for Copilot:**
    > `@COPILOT_GUIDE.md Create a Python module 'vision_analyzer.py' using the 'google.genai' SDK. Define an async function 'analyze_urban_hotspot(image_bytes: bytes, ambient_temp: float, zone_name: str) -> dict'. Use model 'gemini-2.5-flash'. Instruct the model via structured system instructions to return strictly JSON adhering to the schema in COPILOT_GUIDE.md, calculating Heat Vulnerability Index (HVI) from 1 to 10 and detailing passive cross-ventilation corridor recommendations.`

##### Story 1.2: Mock Satellite Asset Seeder
*   **File:** `backend/tools/seed_samples.py`
*   **Prompt for Copilot:**
    > `Write a Python utility script 'seed_samples.py' that creates 3 programmatic test images (RGB PIL images representing: (1) high-density industrial asphalt zone, (2) mixed residential neighborhood with some trees, and (3) green open park). Save them locally in 'data_samples/' and upload them to the GCS bucket defined in 'GCS_BUCKET_NAME' env var.`

---

#### Epic 2: Climate Telemetry & Ingestion Tool
*Goal:* Query ambient temperature anomalies from BigQuery environmental datasets or mock telemetry feeds to ground Gemini's analysis in live weather metrics[span_1](start_span)[span_1](end_span).

##### Story 2.1: Climate Data Retriever
*   **File:** `backend/tools/climate_service.py`
*   **Prompt for Copilot:**
    > `@COPILOT_GUIDE.md Create 'climate_service.py' using 'google.cloud.bigquery'. Implement 'get_latest_temperature(station_id: str = "486980") -> dict' which queries recent daily max and average temperatures from 'bigquery-public-data.noaa_gsod.gsod2024'. Include a local fallback returning realistic high-temperature summer readings (35°C to 41°C) if BigQuery credentials or table quotas are unavailable.`

---

#### Epic 3: Event-Driven Resilience Pipeline
*Goal:* Automatically store historical analysis in Firestore and publish emergency alert events to Pub/Sub when HVI > 8.0[span_2](start_span)[span_2](end_span).

##### Story 3.1: Pub/Sub Publisher Tool
*   **File:** `backend/services/alert_dispatcher.py`
*   **Prompt for Copilot:**
    > `@COPILOT_GUIDE.md Build 'alert_dispatcher.py' with function 'dispatch_heat_alert(zone_data: dict) -> str'. If 'hvi_score' >= 8.0, publish a JSON message payload containing zone coordinates, current temperature, and urgent cooling actions to the Google Cloud Pub/Sub topic from 'PUBSUB_TOPIC_ID'. Return the published message ID.`

##### Story 3.2: Firestore Data Store
*   **File:** `backend/services/database.py`
*   **Prompt for Copilot:**
    > `@COPILOT_GUIDE.md Implement 'database.py' using 'google.cloud.firestore'. Create functions 'save_hotspot_report(report: dict) -> str' to write records to a 'hotspot_scans' collection, and 'get_recent_reports(limit: int = 10) -> list[dict]' to retrieve past scans ordered by timestamp descending.`

---

#### Epic 4: FastAPI Core Service & Agentic Controller
*Goal:* Combine multimodal reasoning, database storage, and alert triggers into clean REST APIs deployable to Cloud Run[span_3](start_span)[span_3](end_span).

##### Story 4.1: FastAPI Controller
*   **File:** `backend/main.py`
*   **Prompt for Copilot:**
    > `@COPILOT_GUIDE.md Create a production-ready FastAPI application in 'backend/main.py'. Enable CORS for frontend development. Expose:
    > 1. 'GET /api/health': checks cloud client readiness.
    > 2. 'POST /api/analyze': accepts an image file upload + ambient temperature float, runs 'vision_analyzer', checks 'climate_service', saves to Firestore via 'database.py', triggers Pub/Sub via 'alert_dispatcher.py' if critical, and returns the unified JSON response.
    > 3. 'GET /api/scans': returns recent scans from Firestore.`

##### Story 4.2: Docker Containerization for Cloud Run
*   **File:** `backend/Dockerfile`
*   **Prompt for Copilot:**
    > `Write a lightweight multi-stage Dockerfile for FastAPI using 'python:3.11-slim'. Set working directory to '/app', copy requirements.txt, install dependencies, expose port 8080 (Cloud Run standard), and define ENTRYPOINT using uvicorn: 'uvicorn main:app --host 0.0.0.0 --port 8080'.`

---

#### Epic 5: Interactive Web Dashboard & Heat Visualizer
*Goal:* Deliver an interactive user interface showing the satellite inspector, live HVI gauge, passive cross-ventilation diagrams, and simulation controls[span_4](start_span)[span_4](end_span).

##### Story 5.1: Streamlit Interactive UI
*   **File:** `frontend/app.py`
*   **Prompt for Copilot:**
    > `@COPILOT_GUIDE.md Create a modern, dark-themed Streamlit dashboard in 'frontend/app.py'.
    > Features:
    > - Left sidebar: City selector (Singapore, Bangkok, Delhi), ambient temperature simulation slider (30°C to 45°C), and preset test image picker (or custom upload).
    > - Main panel: Displays selected aerial photo alongside Gemini's Heat Vulnerability Score (1-10) with colored badges (Green/Yellow/Red).
    > - Passive Cooling Blueprint section: Shows breakdown of asphalt vs canopy percentages, recommended wind-corridor orientation, and cool-roof retrofit potential.
    > - Alert Banner: If score > 8.0, renders a warning banner confirming an automated Pub/Sub emergency notification was dispatched.`

---

### Step-by-Step Execution Sequence in VS Code

1. Run `source setup_gcp.sh` inside the VS Code integrated terminal to ensure all credentials and `.env` variables are active.
2. Create `COPILOT_GUIDE.md` in the project root.
3. Open VS Code Copilot Chat and start with **Story 1.1**, letting Copilot scaffold `backend/services/vision_analyzer.py`.
4. Proceed sequentially through Epics 1 to 5. Run tests at each step using `python backend/main.py` and `streamlit run frontend/app.py`.
