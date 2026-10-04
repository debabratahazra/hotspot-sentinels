import importlib
import os
import socket
from io import BytesIO, StringIO

import dotenv
import pytest
from PIL import Image


def pytest_collection_modifyitems(config, items):
    config._qa_collected_items = tuple(items)


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def deny_external_access(*args, **kwargs):
        raise AssertionError("Tests must not construct real cloud clients or access the network")

    for variable in (
        "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_REGION", "MODEL_ID", "GCS_BUCKET_NAME",
        "GOOGLE_API_KEY", "GEMINI_API_KEY",
    ):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setattr(os, "popen", lambda *args, **kwargs: StringIO(""))
    monkeypatch.setattr(socket.socket, "connect", deny_external_access)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_external_access)
    monkeypatch.setattr(socket, "create_connection", deny_external_access)
    for module_name, client_name in (
        ("google.genai", "Client"),
        ("google.cloud.storage", "Client"),
        ("google.cloud.firestore", "Client"),
        ("google.cloud.pubsub_v1", "PublisherClient"),
        ("google.cloud.bigquery", "Client"),
    ):
        monkeypatch.setattr(importlib.import_module(module_name), client_name, deny_external_access)


@pytest.fixture
def sample_png_bytes():
    output = BytesIO()
    Image.new("RGB", (8, 8), (40, 120, 50)).save(output, format="PNG")
    return output.getvalue()


@pytest.fixture
def valid_report():
    return {
        "zone_id": "qa-zone", "zone_name": "QA District",
        "coordinates": {"lat": 1.3521, "lng": 103.8198},
        "ambient_temp_c": 38.5, "hvi_score": 8.0, "risk_level": "CRITICAL",
        "surface_breakdown": {
            "asphalt_pct": 55, "dark_roof_pct": 30,
            "concrete_pct": 10, "green_canopy_pct": 5,
        },
        "passive_cooling_plan": {
            "corridor_orientation": "NE-SW", "retroreflective_coating_sqm": 4200,
            "micro_canopy_interventions": ["Plant shade corridors"],
            "projected_surface_temp_drop_c": 6.8,
        },
        "alert_dispatched": False, "timestamp": "2026-10-02T12:00:00Z",
    }


@pytest.fixture
def fake_firestore(monkeypatch):
    from unittest.mock import Mock
    from services import database

    client = Mock()
    collection = client.collection.return_value
    document = collection.document.return_value
    document.id = "generated-scan-id"
    query = collection.order_by.return_value.limit.return_value
    query.stream.return_value = []
    monkeypatch.setattr(database, "_get_client", lambda: client)
    return client


@pytest.fixture
def api_environment(monkeypatch, fake_firestore, valid_report):
    from unittest.mock import AsyncMock, Mock
    import main

    analyzer = AsyncMock(return_value=valid_report)
    climate = Mock(return_value={
        "station_id": "486980", "observation_date": None,
        "max_temp_c": 38.5, "avg_temp_c": 32.5, "source": "fallback",
    })
    dispatch = Mock(return_value="published-message-id")
    monkeypatch.setattr(main, "analyze_urban_hotspot", analyzer)
    monkeypatch.setattr(main, "get_latest_temperature", climate)
    monkeypatch.setattr(main, "dispatch_heat_alert", dispatch)
    return main, analyzer, climate, dispatch, fake_firestore