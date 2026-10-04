#!/usr/bin/env python3
"""Validate a Heat Analysis Result payload against the canonical schema and the HVI rules."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "assets" / "heat_analysis_result.schema.json"

# (exclusive upper bound, label) — COPILOT_GUIDE HVI bands
RISK_BANDS = ((4.0, "LOW"), (6.0, "MODERATE"), (8.0, "HIGH"))

TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "number": (int, float),
    "integer": int,
    "null": type(None),
}

REPORT_ENVELOPE_SCHEMA = {
    "climate_source": {
        "type": ["string", "null"],
        "enum": ["bigquery", "fallback", "caller", None],
    },
    "alert_attempted": {"type": ["boolean", "null"]},
    "doc_id": {"type": ["string", "null"], "minLength": 1},
    "identity_source": {
        "type": ["object", "null"],
        "additionalProperties": False,
        "required": ["zone_id", "zone_name", "coordinates"],
        "properties": {
            "zone_id": {"type": "string", "enum": ["supplied", "inferred"]},
            "zone_name": {"type": "string", "enum": ["supplied", "inferred"]},
            "coordinates": {
                "type": "object",
                "additionalProperties": False,
                "required": ["lat", "lng"],
                "properties": {
                    "lat": {"type": "string", "enum": ["supplied", "inferred"]},
                    "lng": {"type": "string", "enum": ["supplied", "inferred"]},
                },
            },
        },
    },
    "image_source": {
        "type": ["string", "null"],
        "enum": ["caller", "google_maps", None],
    },
    "attribution_required": {"type": ["boolean", "null"]},
}
REPORT_ENVELOPE_FIELDS = frozenset(REPORT_ENVELOPE_SCHEMA)


def _matches_type(value, expected: str | list[str]) -> bool:
    if isinstance(expected, list):
        return any(_matches_type(value, candidate) for candidate in expected)
    if expected in ("number", "integer") and isinstance(value, bool):
        return False
    return isinstance(value, TYPES[expected])


def validate_node(value, schema: dict, path: str, errors: list[str]) -> None:
    expected = schema.get("type")
    if expected and not _matches_type(value, expected):
        errors.append(f"{path}: expected {expected}, got {type(value).__name__}")
        return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not one of {schema['enum']}")

    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        errors.append(f"{path}: shorter than minLength {schema['minLength']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} is above maximum {schema['maximum']}")

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                validate_node(item, item_schema, f"{path}[{index}]", errors)

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required key '{key}'")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: unexpected key '{key}'")
        for key, sub_schema in properties.items():
            if key in value:
                validate_node(value[key], sub_schema, f"{path}.{key}", errors)


def expected_risk(hvi: float) -> str:
    for ceiling, label in RISK_BANDS:
        if hvi < ceiling:
            return label
    return "CRITICAL"


def check_business_rules(report: dict, errors: list[str]) -> None:
    for field, schema in REPORT_ENVELOPE_SCHEMA.items():
        if field in report:
            validate_node(report[field], schema, field, errors)

    breakdown = report.get("surface_breakdown")
    if isinstance(breakdown, dict):
        total = sum(v for v in breakdown.values() if isinstance(v, (int, float)) and not isinstance(v, bool))
        if round(total) != 100:
            errors.append(f"surface_breakdown: percentages total {total}, expected 100")

    hvi, risk = report.get("hvi_score"), report.get("risk_level")
    if isinstance(hvi, (int, float)) and isinstance(risk, str):
        wanted = expected_risk(float(hvi))
        if risk != wanted:
            errors.append(f"risk_level: '{risk}' contradicts hvi_score {hvi} (expected '{wanted}')")

    timestamp = report.get("timestamp")
    if isinstance(timestamp, str):
        try:
            parsed = datetime.fromisoformat(timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp)
        except ValueError:
            errors.append(f"timestamp: {timestamp!r} is not ISO-8601")
        else:
            if parsed.utcoffset() != timedelta(0):
                errors.append(f"timestamp: {timestamp!r} must be timezone-aware UTC")

    alert, hvi_value = report.get("alert_dispatched"), report.get("hvi_score")
    if alert is True and isinstance(hvi_value, (int, float)) and hvi_value < 8.0:
        errors.append(f"alert_dispatched: true but hvi_score {hvi_value} is below the 8.0 threshold")

def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_report.py <report.json | ->", file=sys.stderr)
        return 2

    raw = sys.stdin.read() if argv[1] == "-" else Path(argv[1]).read_text(encoding="utf-8")
    try:
        report = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"FAIL — payload is not valid JSON: {exc}")
        return 1

    errors: list[str] = []
    validate_node(report, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")), "$", errors)
    check_business_rules(report, errors)

    if errors:
        print(f"FAIL — {len(errors)} problem(s):")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS — report matches the Heat Analysis Result contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
