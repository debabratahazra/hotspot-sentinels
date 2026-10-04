#!/usr/bin/env python3
"""PostToolUse check: reject edits that violate the COPILOT_GUIDE hard constraints."""

import json
import re
import sys
from pathlib import Path

REGION = "asia-southeast1"
MODEL = "gemini-2.5-flash"

LEGACY_SDK = re.compile(r"^\s*(from\s+vertexai[\w.]*\s+import|import\s+vertexai|from\s+google\s+import\s+generativeai|import\s+google\.generativeai)", re.M)
MODEL_LITERAL = re.compile(r"""["'](gemini-[\w.\-]+)["']""")
REGION_LITERAL = re.compile(r"""(?:location|region|GOOGLE_CLOUD_REGION["'])\s*[=,]\s*["']([a-z]+-[a-z]+\d)["']""", re.I)
CORS_WILDCARD = re.compile(r"""allow_origins\s*=\s*\[\s*["']\*["']""")
CORS_CREDENTIALS = re.compile(r"allow_credentials\s*=\s*True")
FSTRING_OPEN = re.compile(r"""f(\"\"\"|'''|\"|')""")

PATH_KEYS = {"filepath", "file_path", "path", "uri", "target_file", "filename"}


def collect(node, found):
    if isinstance(node, dict):
        for key, value in node.items():
            if key.lower() in PATH_KEYS and isinstance(value, str):
                found.append(value)
            else:
                collect(value, found)
    elif isinstance(node, list):
        for item in node:
            collect(item, found)


def inspect(source: str):
    blockers, warnings = [], []

    if LEGACY_SDK.search(source):
        blockers.append("imports the legacy Vertex AI SDK — use `from google import genai` (COPILOT_GUIDE section 2)")

    for model in set(MODEL_LITERAL.findall(source)):
        if model != MODEL:
            blockers.append(f"pins model '{model}' — this project uses '{MODEL}' via the MODEL_ID env var")

    for region in set(REGION_LITERAL.findall(source)):
        if region.lower() != REGION:
            blockers.append(f"hardcodes region '{region}' — every service defaults to '{REGION}'")

    if CORS_WILDCARD.search(source) and CORS_CREDENTIALS.search(source):
        blockers.append("pairs allow_origins=['*'] with allow_credentials=True — read origins from ALLOWED_ORIGINS instead")

    for match in FSTRING_OPEN.finditer(source):
        window = source[match.end(): match.end() + 300]
        if re.search(r"\bSELECT\b", window, re.I) and "{" in window:
            warnings.append("builds SQL with an f-string — bind values with bigquery.ScalarQueryParameter instead")
            break

    return blockers, warnings


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    paths = []
    collect(payload.get("tool_input") or {}, paths)

    blockers, warnings = [], []
    for raw in paths:
        path = Path(raw)
        if path.suffix != ".py" or not path.is_file():
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        found_blockers, found_warnings = inspect(source)
        blockers += [f"{path.name}: {item}" for item in found_blockers]
        warnings += [f"{path.name}: {item}" for item in found_warnings]

    if blockers:
        json.dump(
            {
                "decision": "block",
                "reason": "Hard constraint violation — fix before continuing:\n- " + "\n- ".join(blockers),
            },
            sys.stdout,
        )
    elif warnings:
        json.dump({"systemMessage": "Review:\n- " + "\n- ".join(warnings)}, sys.stdout)

    sys.exit(0)


if __name__ == "__main__":
    main()
