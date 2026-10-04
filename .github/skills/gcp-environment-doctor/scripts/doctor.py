#!/usr/bin/env python3
"""Diagnose the local HotSpot Sentinels environment. Read-only — changes nothing."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REQUIRED_ENV = ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_REGION", "GCS_BUCKET_NAME", "PUBSUB_TOPIC_ID", "MODEL_ID")
REQUIRED_APIS = ("aiplatform", "run", "storage", "bigquery", "pubsub", "firestore")
REQUIRED_PACKAGES = ("google.genai", "google.cloud.firestore", "google.cloud.pubsub_v1",
                     "google.cloud.bigquery", "google.cloud.storage", "fastapi", "PIL")

results = []


def check(name: str, ok: bool, detail: str = "", fix: str = "") -> bool:
    results.append({"check": name, "ok": ok, "detail": detail, "fix": fix})
    return ok


def gcloud(*args, timeout: int = 30) -> tuple:
    try:
        proc = subprocess.run(("gcloud",) + args, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 1, "", "gcloud unavailable or timed out"


def read_env_file() -> dict:
    path = ROOT / ".env"
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def main() -> int:
    env_file = read_env_file()
    check(".env exists", bool(env_file), f"{len(env_file)} key(s)", "Run ./setup_gcp.sh")

    for key in REQUIRED_ENV:
        present = bool(env_file.get(key) or os.getenv(key))
        check(f".env has {key}", present, "", "Re-run ./setup_gcp.sh to regenerate .env")

    region = env_file.get("GOOGLE_CLOUD_REGION", os.getenv("GOOGLE_CLOUD_REGION", ""))
    check("region is asia-southeast1", region == "asia-southeast1", region or "(unset)",
          "The guide mandates asia-southeast1")

    model = env_file.get("MODEL_ID", os.getenv("MODEL_ID", ""))
    check("model is gemini-2.5-flash", model == "gemini-2.5-flash", model or "(unset)",
          "The guide mandates gemini-2.5-flash")

    missing = [p for p in REQUIRED_PACKAGES if not _importable(p)]
    check("python packages installed", not missing, ", ".join(missing) or "all present",
          "pip install -r requirements.txt")

    if not check("gcloud installed", shutil.which("gcloud") is not None, "", "Install the Google Cloud CLI"):
        return report()

    code, account, _ = gcloud("auth", "list", "--filter=status:ACTIVE", "--format=value(account)")
    check("gcloud authenticated", code == 0 and "@" in account, account or "(none)", "gcloud auth login")

    adc = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
    check("application default credentials", adc.is_file(), "", "gcloud auth application-default login")

    code, active_project, _ = gcloud("config", "get-value", "project")
    configured = env_file.get("GOOGLE_CLOUD_PROJECT", "")
    check("gcloud project matches .env", bool(active_project) and active_project == configured,
          f"gcloud={active_project or '(unset)'} .env={configured or '(unset)'}",
          f"gcloud config set project {configured}" if configured else "Run ./setup_gcp.sh")

    code, enabled, _ = gcloud("services", "list", "--enabled", "--format=value(config.name)", timeout=60)
    if code == 0:
        for api in REQUIRED_APIS:
            check(f"API enabled: {api}", f"{api}.googleapis.com" in enabled, "",
                  f"gcloud services enable {api}.googleapis.com")

    bucket = env_file.get("GCS_BUCKET_NAME", "")
    if bucket:
        code, _, _ = gcloud("storage", "buckets", "describe", f"gs://{bucket}", "--format=value(name)")
        check("GCS bucket exists", code == 0, bucket, f"gcloud storage buckets create gs://{bucket} --location={region}")

    topic = env_file.get("PUBSUB_TOPIC_ID", "")
    if topic:
        code, _, _ = gcloud("pubsub", "topics", "describe", topic, "--format=value(name)")
        check("Pub/Sub topic exists", code == 0, topic, f"gcloud pubsub topics create {topic}")

    code, _, _ = gcloud("firestore", "databases", "describe", "--format=value(name)")
    check("Firestore database exists", code == 0, "",
          f"gcloud firestore databases create --location={region} --type=firestore-native")

    return report()


def _importable(module: str) -> bool:
    return subprocess.run([sys.executable, "-c", f"import {module}"], capture_output=True).returncode == 0


def report() -> int:
    failures = [r for r in results if not r["ok"]]
    if "--json" in sys.argv:
        json.dump({"passed": not failures, "checks": results}, sys.stdout, indent=2)
        print()
        return 1 if failures else 0

    for item in results:
        print(f"{'PASS' if item['ok'] else 'FAIL'}  {item['check']}" + (f"  ({item['detail']})" if item["detail"] else ""))
    if failures:
        print(f"\n{len(failures)} problem(s). Suggested fixes:")
        for item in failures:
            if item["fix"]:
                print(f"  {item['check']}: {item['fix']}")
        return 1
    print("\nEnvironment is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
