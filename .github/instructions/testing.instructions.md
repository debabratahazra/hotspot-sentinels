---
name: "Testing"
description: "Use when writing or fixing pytest tests for HotSpot Sentinels — mocking the Gemini client, Firestore, Pub/Sub and BigQuery, testing FastAPI routes, image fixtures, HVI boundary cases, and the coverage floor."
applyTo: ["tests/**/*.py", "conftest.py"]
---

# Test Rules

## No live cloud, ever

Tests must pass with no credentials and no network. Mock at the client boundary:

```python
@pytest.fixture
def fake_genai(monkeypatch):
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(text=json.dumps(VALID_REPORT))
    monkeypatch.setattr(vision_analyzer, "_get_client", lambda: client)
    return client
```

Never call Vertex AI, write to Firestore, publish to Pub/Sub, or run a BigQuery job from a test. A test that needs credentials is a broken test.

## Layout and naming

Tests live in `tests/`, one module per production module, plus `test_api.py` for routes and `test_contract.py` for schema conformance. Shared fixtures go in `tests/conftest.py`.

Name each test after the behaviour it proves: `test_analyze_raises_on_malformed_json`, not `test_analyze_3`. One acceptance criterion, one test.

## What must be covered

- **Boundaries, not just the happy path.** HVI exactly 4.0, 6.0, and 8.0; percentages summing to 100; an empty scans list; `limit` above the clamp.
- **Error paths.** `VisionAnalysisError` → 502, `DatabaseError` → 503, wrong content type → 415, oversized upload → 413.
- **Contract conformance.** Run representative payloads through `.github/skills/heat-report-validation/scripts/validate_report.py`.
- **Security assertions.** Responses must not leak stack traces, project IDs, bucket names, or topic paths. Assert on that explicitly.

## Fixtures

Generate image fixtures with Pillow inside the fixture — a few hundred bytes, in-memory. Never commit binary test images.

Use `fastapi.testclient.TestClient` for route tests; it needs `httpx`, which is in `requirements.txt`.

## Discipline

- Never edit production code to make a test pass. File a bug instead.
- Never weaken an assertion to go green. `pytest.skip` with a reason, or fix the cause.
- Coverage floor is 70% per touched file. Below that, file a test task rather than silently accepting it.

Run the suite through the sprint tooling so coverage lands in the report:

```bash
python3 .github/skills/agile-sdlc-loop/scripts/sprint_report.py
```
