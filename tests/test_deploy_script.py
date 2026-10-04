"""Offline lint for the Cloud Run deploy script.

BUG-025: four independently fatal defects sat in deploy.sh undetected because no
test ever inspected it. These checks are static — they parse files only and need
no cloud credentials or network, so they run inside the normal offline suite.
"""

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SCRIPT = ROOT / ".github/skills/cloudrun-deploy/scripts/deploy.sh"
DEPLOY_SKILL = ROOT / ".github/skills/cloudrun-deploy/SKILL.md"

# Read by the backend but deliberately not injected at deploy time. Each has a
# safe default and is not environment-specific. Adding a new os.getenv to the
# backend fails the build until it is either injected or recorded here.
INTENTIONALLY_NOT_INJECTED = {
    "MAX_UPLOAD_BYTES",  # contract constant, 10 MB
    "NOAA_GSOD_YEAR",  # dataset year pinned by the climate service
    "PORT",  # Cloud Run injects this itself
}

ENVIRONMENT_NAME = re.compile(r"[A-Z][A-Z0-9_]{2,}")


def backend_environment_names() -> set[str]:
    """Every environment variable the backend reads, derived from its source.

    Matches any call whose name mentions "env", so helpers such as
    `_positive_env_int("GOOGLE_MAPS_REQUEST_LIMIT", ...)` are found alongside
    plain `os.getenv`.
    """
    names: set[str] = set()
    for path in sorted((ROOT / "backend").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            callee = getattr(node.func, "attr", None) or getattr(node.func, "id", "") or ""
            if "env" not in callee.lower():
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                if ENVIRONMENT_NAME.fullmatch(first.value):
                    names.add(first.value)
    return names


def injected_environment_names() -> set[str]:
    match = re.search(r"--set-env-vars\s+\"(.*?)\"", DEPLOY_SCRIPT.read_text(encoding="utf-8"), re.DOTALL)
    assert match, "deploy.sh must inject runtime configuration with --set-env-vars"
    return set(re.findall(r"([A-Z][A-Z0-9_]+)=", match.group(1)))


@pytest.mark.parametrize("service", ["backend", "frontend"])
def test_deploy_builds_each_service_with_its_own_context_and_pins_linux_amd64(service):
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    builds = [line.strip() for line in script.splitlines() if line.strip().startswith("docker build")]
    build = next((line for line in builds if f"-f {service}/Dockerfile" in line), None)
    assert build, f"deploy.sh must build the {service} image; found builds: {builds}"
    # Each Dockerfile's COPY paths are relative to its own directory; a repo-root
    # context cannot resolve them.
    assert build.endswith(f" {service}"), f"{service} build context must be {service}/, got: {build}"
    # Cloud Run rejects arm64, which an Apple-silicon host produces by default.
    assert "--platform linux/amd64" in build, f"{service} image must be pinned to linux/amd64"


def test_deploy_verifies_backend_and_frontend_separately():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    # BUG-026: the dashboard was down for three sprints because only the backend
    # was ever proved. One health check cannot stand in for both services.
    assert "/api/health" in script, "backend must be health-checked"
    assert "/_stcore/health" in script, "frontend must be health-checked; Streamlit is not the API"


def test_deploy_points_the_frontend_at_the_backend_it_just_deployed():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    # Without this the dashboard calls http://localhost:8080 inside its own
    # container and reaches nothing, which is how BUG-026 presented.
    assert re.search(r'--set-env-vars\s+"API_BASE_URL=\$\{?URL\}?"', script), (
        "frontend deploy must set API_BASE_URL to the deployed backend URL"
    )


def test_deploy_injects_every_environment_variable_the_backend_reads():
    required = backend_environment_names() - INTENTIONALLY_NOT_INJECTED
    missing = required - injected_environment_names()
    assert not missing, (
        f"deploy.sh does not inject {sorted(missing)}. Either add them to --set-env-vars "
        "or record them in INTENTIONALLY_NOT_INJECTED with a reason."
    )


@pytest.mark.parametrize("name", ["GOOGLE_MAPS_API_KEY", "BIGQUERY_LOCATION"])
def test_deploy_injects_the_variables_whose_absence_broke_production(name):
    # Both were missing in BUG-025: no Maps key meant every coordinate analysis
    # returned 502, and BIGQUERY_LOCATION is the ratified asia-southeast1 exception.
    assert name in injected_environment_names()


def test_deploy_aborts_when_the_maps_key_is_unset():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    assert re.search(r':\s*"\$\{GOOGLE_MAPS_API_KEY:\?', script), (
        "deploy.sh must refuse to ship a revision that would 502 on coordinate analysis"
    )


def test_deploy_service_name_matches_the_documented_verify_and_rollback_commands():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    default = re.search(r'SERVICE="\$\{SERVICE_NAME:-([a-z0-9-]+)\}"', script)
    assert default, "deploy.sh must define an overridable default service name"
    service = default.group(1)

    skill = DEPLOY_SKILL.read_text(encoding="utf-8")
    documented = set(re.findall(r"gcloud run services (?:describe|update-traffic) ([a-z0-9-]+)", skill))
    assert documented, "the skill must document verify and rollback commands"
    assert service in documented, (
        f"deploy.sh deploys '{service}' but the skill documents {sorted(documented)}; "
        "deploying under a different name creates a second service instead of a new revision"
    )


def test_deploy_separates_environment_values_without_splitting_multi_origin_cors():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    # ALLOWED_ORIGINS may itself contain commas, so the default comma delimiter
    # would silently split one value into several environment variables.
    assert "--set-env-vars \"^@^" in script, "use a non-comma delimiter for --set-env-vars"
