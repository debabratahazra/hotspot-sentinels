import ast
import asyncio
import inspect
import json
import runpy
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi import UploadFile
from pydantic import BaseModel, ValidationError

from services.vision_analyzer import HotspotAnalysisResult

REPORT_ENVELOPE = {
    "climate_source", "alert_attempted", "doc_id", "identity_source",
    "image_source", "attribution_required",
}
STORAGE_ENVELOPE = {"created_at"}


@pytest.fixture
def report_validator():
    return runpy.run_path(str(Path(".github/skills/heat-report-validation/scripts/validate_report.py")))


@pytest.mark.parametrize("timestamp", [
    "2026-10-03T12:00:00", "2026-10-03T12:00:00+08:00",
    "2026-10-03T12:00:00-05:00",
])
def test_validator_rejects_naive_and_non_utc_timestamps(report_validator, valid_report, monkeypatch, capsys, timestamp):
    valid_report["timestamp"] = timestamp
    monkeypatch.setattr("sys.stdin", StringIO(json.dumps(valid_report)))
    assert report_validator["main"](["validate_report.py", "-"]) == 1
    assert capsys.readouterr().out == (
        f"FAIL \u2014 1 problem(s):\n  - timestamp: {timestamp!r} must be timezone-aware UTC\n"
    )


@pytest.mark.parametrize("timestamp", ["2026-10-03T12:00:00Z", "2026-10-03T12:00:00+00:00"])
def test_validator_accepts_both_utc_timestamp_spellings(report_validator, valid_report, monkeypatch, capsys, timestamp):
    valid_report["timestamp"] = timestamp
    monkeypatch.setattr("sys.stdin", StringIO(json.dumps(valid_report)))
    assert report_validator["main"](["validate_report.py", "-"]) == 0
    assert capsys.readouterr().out == "PASS \u2014 report matches the Heat Analysis Result contract\n"


def test_validator_normalizes_z_for_python_310_parser(report_validator, valid_report, monkeypatch):
    parser = Mock()
    parser.fromisoformat.side_effect = lambda value: datetime.fromisoformat(value) if not value.endswith("Z") else pytest.fail("Python 3.10 cannot parse Z")
    monkeypatch.setitem(report_validator["check_business_rules"].__globals__, "datetime", parser)
    errors = []
    report_validator["check_business_rules"](valid_report, errors)
    assert errors == []
    parser.fromisoformat.assert_called_once_with("2026-10-02T12:00:00+00:00")


def test_validator_still_rejects_malformed_timestamps(report_validator, valid_report):
    valid_report["timestamp"] = "not-a-timestamp"
    errors = []
    report_validator["check_business_rules"](valid_report, errors)
    assert errors == ["timestamp: 'not-a-timestamp' is not ISO-8601"]


@pytest.mark.parametrize("score,band", [(3.9, "LOW"), (4.0, "MODERATE"), (6.0, "HIGH"), (8.0, "CRITICAL")])
def test_canonical_validator_accepts_every_hvi_boundary(report_validator, valid_report, score, band):
    valid_report.update(hvi_score=score, risk_level=band)
    errors = []
    report_validator["validate_node"](valid_report, json.loads(report_validator["SCHEMA_PATH"].read_text()), "$", errors)
    report_validator["check_business_rules"](valid_report, errors)
    assert errors == []


@pytest.mark.parametrize("field,value,expected_error", [
    ("zone_id", "", "shorter than minLength"),
    ("hvi_score", True, "expected number"),
    ("hvi_score", 0.0, "below minimum"),
    ("hvi_score", 11.0, "above maximum"),
    ("risk_level", "EXTREME", "not one of"),
    ("coordinates", {"lat": 1.0, "lng": 2.0, "altitude": 3.0}, "unexpected key"),
    ("coordinates", {"lat": 1.0}, "missing required key"),
    ("surface_breakdown", {"asphalt_pct": 54, "dark_roof_pct": 30,
                           "concrete_pct": 10, "green_canopy_pct": 5}, "percentages total 99"),
    ("passive_cooling_plan", {"corridor_orientation": "NE-SW", "retroreflective_coating_sqm": 1,
                             "micro_canopy_interventions": [], "projected_surface_temp_drop_c": 1},
     "needs at least 1 item"),
    ("passive_cooling_plan", {"corridor_orientation": "NE-SW", "retroreflective_coating_sqm": 1,
                             "micro_canopy_interventions": [False], "projected_surface_temp_drop_c": 1},
     "expected string"),
    ("risk_level", "LOW", "contradicts hvi_score"),
], ids=["empty-identity", "boolean-number", "below-minimum", "above-maximum",
        "invalid-enum", "unknown-nested-key", "missing-coordinate", "surface-total",
        "empty-interventions", "wrong-array-item", "risk-mismatch"])
def test_canonical_validator_rejects_malformed_payload_fields(
    report_validator, valid_report, field, value, expected_error,
):
    valid_report[field] = value
    errors = []
    report_validator["validate_node"](valid_report, json.loads(report_validator["SCHEMA_PATH"].read_text()), "$", errors)
    report_validator["check_business_rules"](valid_report, errors)
    assert any(expected_error in error for error in errors), errors


def test_canonical_validator_rejects_alert_dispatched_below_threshold(report_validator, valid_report):
    valid_report.update(hvi_score=6.0, risk_level="HIGH", alert_dispatched=True)
    errors = []
    report_validator["check_business_rules"](valid_report, errors)
    assert errors == ["alert_dispatched: true but hvi_score 6.0 is below the 8.0 threshold"]


def test_validator_cli_rejects_invalid_json(report_validator, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", StringIO("{not-json"))
    assert report_validator["main"](["validate_report.py", "-"]) == 1
    assert "payload is not valid JSON" in capsys.readouterr().out


def test_validator_cli_requires_exactly_one_input_argument(report_validator, capsys):
    assert report_validator["main"](["validate_report.py"]) == 2
    assert "usage:" in capsys.readouterr().err


def test_validator_script_entry_point_validates_real_stdin(valid_report, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", StringIO(json.dumps(valid_report)))
    monkeypatch.setattr("sys.argv", ["validate_report.py", "-"])
    with pytest.raises(SystemExit) as exit_result:
        runpy.run_path(".github/skills/heat-report-validation/scripts/validate_report.py", run_name="__main__")
    assert exit_result.value.code == 0
    assert "PASS" in capsys.readouterr().out


def test_validator_handles_array_schema_without_item_constraints(report_validator):
    errors = []
    report_validator["validate_node"]([1, "unconstrained"], {"type": "array"}, "$", errors)
    assert errors == []


def test_business_rules_defer_absent_or_wrong_typed_fields_to_schema(report_validator):
    errors = []
    report_validator["check_business_rules"]({"surface_breakdown": None, "hvi_score": None, "timestamp": 123}, errors)
    assert errors == []
    report_validator["validate_node"](
        {"surface_breakdown": None, "hvi_score": None, "timestamp": 123},
        json.loads(report_validator["SCHEMA_PATH"].read_text()), "$", errors,
    )
    assert any("expected object" in error for error in errors)
    assert any("expected number" in error for error in errors)
    assert any("expected string" in error for error in errors)


@pytest.mark.parametrize("source", [
    {"zone_id": "supplied", "zone_name": "supplied", "coordinates": {"lat": "supplied", "lng": "supplied"}},
    {"zone_id": "inferred", "zone_name": "inferred", "coordinates": {"lat": "inferred", "lng": "inferred"}},
    {"zone_id": "supplied", "zone_name": "inferred", "coordinates": {"lat": "supplied", "lng": "inferred"}},
    {"zone_id": "inferred", "zone_name": "supplied", "coordinates": {"lat": "inferred", "lng": "supplied"}},
], ids=["all-supplied", "all-inferred", "mixed-lat", "mixed-lng"])
def test_identity_source_serialization_preserves_all_four_distinctions(report_validator, valid_report, source):
    import main
    from services.vision_analyzer import IdentitySource

    valid_report["identity_source"] = IdentitySource.model_validate(source).model_dump()
    serialized = main.AnalysisResponse.model_validate(valid_report).model_dump(mode="json")
    assert serialized["identity_source"] == source
    errors = []
    report_validator["validate_node"](serialized, json.loads(report_validator["SCHEMA_PATH"].read_text()), "$", errors)
    report_validator["check_business_rules"](serialized, errors)
    assert errors == []


@pytest.mark.parametrize("source,expected_error", [
    ({"zone_id": "fabricated", "zone_name": "inferred",
      "coordinates": {"lat": "supplied", "lng": "inferred"}}, "identity_source.zone_id"),
    ({"zone_id": "supplied", "coordinates": {"lat": "supplied", "lng": "inferred"}},
     "missing required key 'zone_name'"),
    ({"zone_id": "supplied", "zone_name": "inferred",
      "coordinates": {"lat": "supplied"}}, "missing required key 'lng'"),
    ({"zone_id": "supplied", "zone_name": "inferred",
      "coordinates": {"lat": "supplied", "lng": "estimated"}}, "identity_source.coordinates.lng"),
    ({"zone_id": "supplied", "zone_name": "inferred",
      "coordinates": {"lat": "supplied", "lng": "inferred", "altitude": "supplied"}},
     "unexpected key 'altitude'"),
], ids=["invalid-identity-origin", "missing-identity-origin", "missing-coordinate-origin",
        "invalid-coordinate-origin", "extra-coordinate-origin"])
def test_canonical_validator_rejects_malformed_identity_provenance(
    report_validator, valid_report, source, expected_error,
):
    valid_report["identity_source"] = source
    errors = []
    report_validator["validate_node"](
        valid_report, json.loads(report_validator["SCHEMA_PATH"].read_text()), "$", errors
    )
    report_validator["check_business_rules"](valid_report, errors)
    assert any(expected_error in error for error in errors), errors


def test_canonical_validator_accepts_all_report_envelope_fields(report_validator, valid_report):
    valid_report.update(
        climate_source="caller",
        alert_attempted=True,
        doc_id="qa-document-id",
        identity_source={
            "zone_id": "supplied", "zone_name": "inferred",
            "coordinates": {"lat": "supplied", "lng": "inferred"},
        },
        image_source="google_maps",
        attribution_required=True,
    )
    errors = []
    report_validator["validate_node"](
        valid_report, json.loads(report_validator["SCHEMA_PATH"].read_text()), "$", errors
    )
    report_validator["check_business_rules"](valid_report, errors)
    assert errors == []


def test_contract_test_allowlist_matches_application_and_validator(report_validator):
    import main

    application_fields = set(main.AnalysisResponse.model_fields) - set(HotspotAnalysisResult.model_fields)
    assert application_fields == REPORT_ENVELOPE
    assert application_fields == set(report_validator["REPORT_ENVELOPE_SCHEMA"])


@pytest.mark.parametrize("field,value,expected_error", [
    ("climate_source", "telemetry", "climate_source"),
    ("alert_attempted", "yes", "alert_attempted"),
    ("doc_id", "", "doc_id"),
    ("image_source", "satellite", "image_source"),
    ("attribution_required", 1, "attribution_required"),
], ids=["invalid-climate-source", "wrong-alert-type", "empty-doc-id",
        "invalid-image-source", "wrong-attribution-type"])
def test_canonical_validator_rejects_malformed_report_envelope_fields(
    report_validator, valid_report, field, value, expected_error,
):
    valid_report[field] = value
    errors = []
    report_validator["validate_node"](
        valid_report, json.loads(report_validator["SCHEMA_PATH"].read_text()), "$", errors
    )
    report_validator["check_business_rules"](valid_report, errors)
    assert any(expected_error in error for error in errors), errors


@pytest.mark.parametrize("source", [
    {"zone_id": "fabricated", "zone_name": "inferred", "coordinates": {"lat": "supplied", "lng": "inferred"}},
    {"zone_id": "supplied", "zone_name": 123, "coordinates": {"lat": "supplied", "lng": "inferred"}},
    {"zone_id": "supplied", "zone_name": "inferred", "coordinates": {"lat": "supplied"}},
    {"zone_id": "supplied", "zone_name": "inferred", "coordinates": {"lat": "supplied", "lng": "inferred", "altitude": "supplied"}},
], ids=["invalid-origin", "wrong-type", "missing-longitude-origin", "extra-coordinate-origin"])
def test_api_response_model_rejects_malformed_identity_provenance(valid_report, source):
    import main

    valid_report["identity_source"] = source
    with pytest.raises(ValidationError) as rejected:
        main.AnalysisResponse.model_validate(valid_report)
    assert all(error["loc"][0] == "identity_source" for error in rejected.value.errors())


def test_real_analyzer_generated_payload_passes_utc_validator(report_validator, valid_report, sample_png_bytes, monkeypatch):
    from services import vision_analyzer

    client = Mock()
    client.models.generate_content.return_value.text = json.dumps(valid_report)
    monkeypatch.setattr(vision_analyzer, "get_client", lambda: client)
    report = asyncio.run(vision_analyzer.analyze_urban_hotspot(sample_png_bytes, 38.5, mime_type="image/png"))
    assert report["timestamp"].endswith("+00:00")
    errors = []
    report_validator["validate_node"](report, json.loads(report_validator["SCHEMA_PATH"].read_text()), "$", errors)
    report_validator["check_business_rules"](report, errors)
    assert errors == []


@pytest.mark.parametrize("stored_timestamp", [
    datetime(2026, 10, 3, 12, tzinfo=timezone.utc),
    datetime(2026, 10, 3, 20, tzinfo=timezone(timedelta(hours=8))),
    datetime(2026, 10, 3, 12),
])
def test_real_database_serialized_timestamp_passes_utc_validator(report_validator, valid_report, fake_firestore, stored_timestamp):
    from services import database

    valid_report["timestamp"] = stored_timestamp
    document = Mock()
    document.to_dict.return_value = valid_report
    fake_firestore.collection.return_value.order_by.return_value.limit.return_value.stream.return_value = [document]
    report = database.get_recent_reports()[0]
    assert report["timestamp"] == "2026-10-03T12:00:00+00:00"
    errors = []
    report_validator["validate_node"](report, json.loads(report_validator["SCHEMA_PATH"].read_text()), "$", errors)
    report_validator["check_business_rules"](report, errors)
    assert errors == []


def unawaited_coroutine_calls(tree, namespace):
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    def resolve(target):
        if isinstance(target, ast.Name):
            return namespace.get(target.id)
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
            return getattr(namespace.get(target.value.id), target.attr, None)
        return None

    def consumed(node):
        parent = parents.get(node)
        if isinstance(parent, ast.Await):
            return True
        if isinstance(parent, ast.Call) and node in parent.args:
            consumer = resolve(parent.func)
            if consumer in (asyncio.create_task, asyncio.ensure_future, asyncio.run):
                return True
            if consumer in (asyncio.gather, asyncio.wait_for, asyncio.shield):
                return consumed(parent)
        return False

    failures = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if resolve(node.func) is asyncio.to_thread and node.args and inspect.iscoroutinefunction(resolve(node.args[0])):
            failures.append((node.lineno, "asyncio.to_thread cannot consume an async callable"))
        if inspect.iscoroutinefunction(resolve(node.func)) and not consumed(node):
            failures.append((node.lineno, ast.unparse(node.func)))
    return failures


def test_main_awaits_every_coroutine_function_it_calls():
    import main

    namespace = dict(vars(main), file=UploadFile)
    tree = ast.parse(Path("backend/main.py").read_text())
    assert not unawaited_coroutine_calls(tree, namespace)


def test_coroutine_regression_guard_rejects_bare_calls_and_import_aliases():
    async def coroutine():
        return {}

    namespace = {"alias": coroutine}
    assert unawaited_coroutine_calls(ast.parse("alias()"), namespace) == [(1, "alias")]
    assert not unawaited_coroutine_calls(ast.parse("async def route():\n    await alias()"), namespace)


@pytest.mark.parametrize("expression", [
    "await aio.gather(alias())",
    "await aio.wait_for(alias(), timeout=1)",
    "await aio.wait_for(aio.gather(alias()), timeout=1)",
    "aio.create_task(alias())",
])
def test_coroutine_regression_guard_accepts_consumed_wrappers_and_scheduled_tasks(expression):
    async def coroutine():
        return {}

    namespace = {"alias": coroutine, "aio": asyncio}
    assert not unawaited_coroutine_calls(ast.parse(f"async def route():\n    {expression}"), namespace)


@pytest.mark.parametrize("expression", [
    "aio.gather(alias())",
    "aio.wait_for(alias(), timeout=1)",
    "aio.wait_for(aio.gather(alias()), timeout=1)",
    "await aio.to_thread(alias)",
])
def test_coroutine_regression_guard_rejects_unconsumed_wrappers(expression):
    async def coroutine():
        return {}

    failures = unawaited_coroutine_calls(
        ast.parse(f"async def route():\n    {expression}"), {"alias": coroutine, "aio": asyncio}
    )
    assert failures


def schema_reference_errors(tree):
    root_fields = set(HotspotAnalysisResult.model_fields)
    extensions = REPORT_ENVELOPE | STORAGE_ENVELOPE
    shapes = {name: root_fields | extensions for name in ("report", "data", "scan", "analysis_report", "stored_report", "zone_data")}
    for name, field in HotspotAnalysisResult.model_fields.items():
        if isinstance(field.annotation, type) and issubclass(field.annotation, BaseModel):
            shapes[name] = set(field.annotation.model_fields)
    shapes["plan"] = shapes["passive_cooling_plan"]
    shapes["surfaces"] = shapes["surface_breakdown"]
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            value = node.value
            if isinstance(value, ast.BoolOp):
                value = value.values[0]
            owner, key = access(value)
            shape = shapes.get(key) if owner in shapes else shapes.get(value.id) if isinstance(value, ast.Name) else None
            if shape is not None:
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id not in shapes:
                        shapes[target.id] = shape
                        changed = True
    failures = []
    for node in ast.walk(tree):
        owner, key = access(node)
        if owner in shapes and key is not None and key not in shapes[owner]:
            failures.append((node.lineno, owner, key))
    return failures


def access(node):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args:
        owner, key = node.func.value, node.args[0]
    elif isinstance(node, ast.Subscript):
        owner, key = node.value, node.slice
    else:
        return None, None
    if isinstance(owner, ast.Name) and isinstance(key, ast.Constant) and isinstance(key.value, str):
        return owner.id, key.value
    return None, None


def test_no_production_module_references_fields_absent_from_report_schema():
    files = [*Path("backend").rglob("*.py"), *Path("frontend").rglob("*.py")]
    failures = {}
    for path in files:
        if path.name.startswith("test_"):
            continue
        errors = schema_reference_errors(ast.parse(path.read_text()))
        if errors:
            failures[str(path)] = errors
    assert not failures, failures


def test_schema_regression_guard_rejects_deleted_nested_and_aliased_fields():
    tree = ast.parse("alias = report\nalias.get('requires_emergency_alert')\nplan = data.get('passive_cooling_plan') or {}\nplan.get('surface_temp_estimate_c')")
    assert schema_reference_errors(tree) == [(2, "alias", "requires_emergency_alert"), (4, "plan", "surface_temp_estimate_c")]