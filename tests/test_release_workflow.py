"""Offline lint for the keyless release workflow (STORY-043).

Static parsing only: no cloud credentials, no network. These encode the acceptance
criteria so the workflow cannot silently drift away from them.
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / ".github/workflows/release.yml"


def workflow() -> dict:
    # PyYAML parses the `on:` key as boolean True (YAML 1.1), so read it back by value.
    return yaml.safe_load(RELEASE.read_text(encoding="utf-8"))


def triggers() -> dict:
    loaded = workflow()
    return loaded.get("on") or loaded.get(True)


def steps() -> list[dict]:
    return [step for job in workflow()["jobs"].values() for step in job.get("steps", [])]


def script() -> str:
    return RELEASE.read_text(encoding="utf-8")


def test_release_runs_only_for_semver_tags_and_never_for_pull_requests():
    on = triggers()
    assert set(on) == {"push"}, f"release must trigger on push tags only, got {sorted(on)}"
    assert "branches" not in on["push"], "a branch push must not deploy"
    patterns = on["push"]["tags"]
    assert patterns == ["v[0-9]+.[0-9]+.[0-9]+"], f"tags must be vMAJOR.MINOR.PATCH, got {patterns}"
    # A fork pull request must never reach Google Cloud.
    assert "pull_request" not in on and "pull_request_target" not in on


def test_release_requests_an_oidc_token_and_uses_no_key_file():
    assert workflow()["permissions"]["id-token"] == "write"
    auth = next((s for s in steps() if "google-github-actions/auth" in str(s.get("uses", ""))), None)
    assert auth, "release must authenticate with google-github-actions/auth"
    assert "workload_identity_provider" in auth["with"]
    assert "service_account" in auth["with"]
    # credentials_json is the key-file path; it must never appear.
    assert "credentials_json" not in auth["with"], "key-file auth is forbidden"
    assert "credentials_json" not in script()


def test_release_gate_requires_main_and_every_required_check():
    text = script()
    assert "merge-base --is-ancestor" in text, "the tagged commit must be proven to be on main"
    for name in (
        "Offline suite and coverage floor",
        "Generated dependency exports are current",
        "Build backend image",
        "Build frontend image",
        "Secret scan",
    ):
        assert name in text, f"release gate must require the {name!r} check"


@pytest.mark.parametrize("service", ["backend", "frontend"])
def test_release_builds_each_service_from_its_own_context_on_amd64(service):
    builds = [line.strip() for line in script().splitlines() if line.strip().startswith("docker build")]
    build = next((line for line in builds if f"-f {service}/Dockerfile" in line), None)
    assert build, f"release must build the {service} image"
    assert build.endswith(f" {service}"), f"{service} context must be {service}/"
    assert "--platform linux/amd64" in build, "Cloud Run rejects arm64"


def test_release_preserves_the_bigquery_location_exception():
    env_block = re.search(r'--set-env-vars "(.*?)"', script(), re.DOTALL)
    assert env_block, "backend deploy must inject runtime configuration"
    assert "BIGQUERY_LOCATION=US" in env_block.group(1), (
        "NOAA GSOD is US multi-region; losing this makes every climate query fail"
    )


def test_release_mounts_the_maps_key_as_a_secret_not_an_environment_variable():
    text = script()
    env_blocks = re.findall(r'--set-env-vars "(.*?)"', text, re.DOTALL)
    assert not any("GOOGLE_MAPS_API_KEY" in block for block in env_blocks), (
        "env var values are readable with run.services.get; mount the key with --set-secrets"
    )
    assert re.search(r'--set-secrets "GOOGLE_MAPS_API_KEY=', text)


def test_release_verifies_both_services_separately_and_analyses_a_coordinate():
    text = script()
    # BUG-026: a healthy backend is not evidence the dashboard works.
    assert "/api/health" in text, "backend health must be checked"
    assert "/_stcore/health" in text, "frontend health must be checked; Streamlit is not the API"
    assert "/api/analyze" in text, "release evidence must include a coordinate analysis"


def test_release_consumes_no_github_secrets():
    # The Maps key lives in Secret Manager, so the workflow needs no repository secret.
    assert "secrets." not in script(), "release must not depend on any GitHub secret"
