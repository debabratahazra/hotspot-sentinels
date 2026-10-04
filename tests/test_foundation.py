import importlib
import os
import re
import shutil
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VARIABLES = {
    "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_REGION", "GCS_BUCKET_NAME",
    "PUBSUB_TOPIC_ID", "MODEL_ID", "ALLOWED_ORIGINS", "PORT",
    "GOOGLE_MAPS_API_KEY",
}
SECRET_VARIABLES = {"GOOGLE_MAPS_API_KEY"}


def local_command(arguments, *, cwd=ROOT, env=None):
    return subprocess.run(arguments, cwd=cwd, env=env, capture_output=True, text=True, check=False)


def test_git_status_runs():
    result = local_command(["git", "status", "--porcelain"])
    assert result.returncode == 0, result.stderr
    assert local_command(["git", "rev-parse", "--is-inside-work-tree"]).stdout.strip() == "true"


def test_no_env_or_credential_file_is_tracked():
    result = local_command(["git", "ls-files", "-z"])
    assert result.returncode == 0
    forbidden = re.compile(r"(^|/)(\.env($|\.(?!example$))|credentials\.json$|.*[-_]key\.json$|service-account.*\.json$)|\.(pem|p12|pfx)$")
    assert not [name for name in result.stdout.split("\0") if forbidden.search(name)]


@pytest.mark.parametrize("filename", [
    ".env", "credentials.json", "qa-key.json", "qa_key.json", "service-account-qa.json",
    "qa.pem", "qa.p12", "qa.pfx", "venv/lib", "__pycache__/qa.pyc",
    ".pytest_cache/qa", ".coverage", "coverage.json", "data_samples/qa.png",
])
def test_secrets_and_build_artifacts_are_ignored(filename):
    assert local_command(["git", "check-ignore", "-q", filename]).returncode == 0


@pytest.mark.parametrize("filename", [".env.example", "agile/backlog.json", "agile/reports/sprint-01.md"])
def test_template_and_sprint_evidence_are_not_ignored(filename):
    assert local_command(["git", "check-ignore", "-q", filename]).returncode == 1


def test_env_template_is_not_ignored_but_env_is_ignored():
    assert local_command(["git", "check-ignore", "-q", ".env.example"]).returncode == 1
    assert local_command(["git", "check-ignore", "-q", ".env"]).returncode == 0


def test_env_example_contains_eight_contract_variables_without_secrets():
    from dotenv import dotenv_values

    result = local_command(["grep", "-E", "^[A-Z_]+=", ".env.example"])
    assert result.returncode == 0, "Template assignments could not be read through subprocess"
    assert len(result.stdout.splitlines()) == 8
    values = dotenv_values(stream=StringIO(result.stdout), interpolate=False)
    assert set(values) == CONTRACT_VARIABLES
    assert values["GOOGLE_CLOUD_PROJECT"] == ""
    assert values["GCS_BUCKET_NAME"] == ""
    assert values["GOOGLE_CLOUD_REGION"] == "asia-southeast1"
    for name in SECRET_VARIABLES:
        assert values[name] == "", (
            f"{name} holds a credential and .env.example is committed; "
            "the template must declare the name with an empty value only"
        )
    for value in values.values():
        assert value is not None
        assert not any(marker in value for marker in ("ya29.", "Bearer", "-----BEGIN"))
        assert re.search(r"[A-Za-z0-9+/=_-]{40,}", value) is None


def test_setup_script_honours_a_supplied_pubsub_topic_id():
    source = (ROOT / "setup_gcp.sh").read_text(encoding="utf-8")
    assert re.search(r'export PUBSUB_TOPIC="\$\{PUBSUB_TOPIC_ID:-heat-resilience-alerts\}"', source), (
        "setup_gcp.sh must provision the configured topic, not a bare literal"
    )
    # The topic it creates and the topic it writes into .env must be the same value,
    # or provisioning and runtime configuration silently disagree.
    assert "PUBSUB_TOPIC_ID=${PUBSUB_TOPIC}" in source
    assert "gcloud pubsub topics create $PUBSUB_TOPIC" in source


def test_setup_script_emits_allowed_origins_and_all_contract_variables():
    source = (ROOT / "setup_gcp.sh").read_text(encoding="utf-8")
    match = re.search(r"cat\s*<<\s*EOF\s*>\s*\.env\s*\n(.*?)\nEOF", source, re.DOTALL)
    assert match is not None
    values = dict(line.split("=", 1) for line in match.group(1).splitlines())
    assert CONTRACT_VARIABLES <= values.keys()
    assert all(values[key] for key in CONTRACT_VARIABLES - SECRET_VARIABLES)
    for name in SECRET_VARIABLES:
        assert values[name] == "", (
            f"setup_gcp.sh must declare {name} for the operator to fill in, "
            "never provision or inline a credential value"
        )
    assert values["ALLOWED_ORIGINS"] == "http://localhost:8501"
    assert values["PORT"] == "8080"


def test_execution_spec_uses_existing_setup_script():
    source = (ROOT / "Epics_Stories.md").read_text(encoding="utf-8")
    assert "source setup_gcp.sh" in source
    assert "setup_gcp" + ".zsh" not in source
    assert (ROOT / "setup_gcp.sh").is_file()


def test_active_execution_docs_have_no_obsolete_setup_command():
    for filename in ("README.md", "COPILOT_GUIDE.md", "Epics_Stories.md", "setup_gcp.sh"):
        assert "setup_gcp" + ".zsh" not in (ROOT / filename).read_text(encoding="utf-8")


def test_tools_package_init_exists():
    assert (ROOT / "backend/tools/__init__.py").is_file()


def test_services_and_tools_import_from_backend_working_directory():
    result = local_command(
        [sys.executable, "-c", "import services.vision_analyzer; import tools; print('backend imports PASS')"],
        cwd=ROOT / "backend",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "backend imports PASS"


def test_pytest_import_strategy_is_configured_and_documented(pytestconfig):
    assert [Path(path).resolve() for path in pytestconfig.getini("pythonpath")] == [ROOT / "backend"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "pythonpath" in readme
    assert "pytest" in readme
    assert "services" in readme
    assert "tools" in readme


def test_import_strategy_documents_service_tool_layering():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "services" in readme
    assert "tools" in readme
    assert "main" in readme
    assert "neither" in readme.lower() or "must not" in readme.lower()


def test_no_cloud_calling_scripts_live_under_backend(pytestconfig):
    assert pytestconfig.getini("testpaths") == ["tests"]
    assert not (ROOT / "backend/test_analyzer.py").exists()
    assert not (ROOT / "backend/test_pipeline.py").exists()
    assert not any(
        item.path.parent == ROOT / "backend" and item.path.name.startswith("test_")
        for item in pytestconfig._qa_collected_items
    )


def project_metadata():
    try:
        import tomllib
    except ImportError:
        import toml
        return toml.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def offline_uv(arguments, *, env=None):
    executable = shutil.which("uv")
    assert executable, "uv is required to prove the dependency acceptance criteria"
    environment = dict(os.environ, UV_OFFLINE="1", UV_PYTHON_DOWNLOADS="never", UV_NO_PROGRESS="1")
    if env:
        environment.update(env)
    return local_command([executable, *arguments], env=environment)


def test_python_support_is_310_and_uv_lock_is_current():
    assert project_metadata()["project"]["requires-python"] == ">=3.10"
    result = offline_uv(["lock", "--check"])
    assert result.returncode == 0, result.stderr


def test_manifest_contains_backend_frontend_and_test_dependencies():
    metadata = project_metadata()
    core = {Requirement(requirement).name for requirement in metadata["project"]["dependencies"]}
    frontend = {Requirement(requirement).name for requirement in metadata["dependency-groups"]["frontend"]}
    dev = {Requirement(requirement).name for requirement in metadata["dependency-groups"]["dev"]}
    assert "requests" in core
    assert "streamlit" in frontend
    assert "streamlit" not in core | dev
    requirements = (metadata["project"]["dependencies"]
                    + metadata["dependency-groups"]["frontend"]
                    + metadata["dependency-groups"]["dev"])
    packages = {Requirement(requirement).name for requirement in requirements}
    assert {
        "google-genai", "google-cloud-aiplatform", "google-cloud-bigquery", "google-cloud-firestore",
        "google-cloud-pubsub", "google-cloud-storage", "fastapi", "uvicorn", "pydantic", "pillow",
        "python-dotenv", "python-multipart", "streamlit", "requests", "pytest", "pytest-cov", "httpx",
    } <= packages


def test_uv_export_reproduces_requirements_dependency_content():
    for filename, groups in (
        ("requirements.txt", ["--group", "frontend", "--group", "dev"]),
        ("backend/requirements.txt", ["--no-dev"]),
    ):
        arguments = ["export", "--locked", *groups, "--no-hashes", "--no-emit-project"]
        regeneration = "uv " + " ".join([*arguments, "--output-file", filename])
        result = offline_uv([*arguments, "--no-header"])
        assert result.returncode == 0, result.stderr
        manifest = (ROOT / filename).read_text(encoding="utf-8")
        header = (
            "# This file was autogenerated by uv via the following command:\n"
            f"#    {regeneration}\n"
        )
        assert manifest.startswith(header)
        assert header + result.stdout == manifest, f"Generated export differs: {filename}"
        packages = {Requirement(line.strip()).name for line in manifest.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")}
        if filename == "requirements.txt":
            assert {"fastapi", "streamlit", "requests", "pytest", "pytest-cov", "httpx"} <= packages
        else:
            assert {"fastapi", "requests"} <= packages
            assert not {"streamlit", "altair", "pyarrow"} & packages


def test_required_packages_importable():
    for module_name in (
        "google.genai", "google.cloud.aiplatform", "google.cloud.bigquery", "google.cloud.firestore",
        "google.cloud.pubsub_v1", "google.cloud.storage", "fastapi", "uvicorn", "pydantic", "PIL",
        "dotenv", "multipart", "streamlit", "requests", "pytest", "pytest_cov", "httpx",
    ):
        assert importlib.import_module(module_name) is not None


def test_clean_offline_environment_imports_required_packages(tmp_path):
    environment = tmp_path / "clean-environment"
    result = offline_uv(
        ["sync", "--locked", "--group", "frontend", "--group", "dev",
         "--no-install-project", "--python", sys.executable],
        env={"UV_PROJECT_ENVIRONMENT": str(environment)},
    )
    assert result.returncode == 0, result.stderr
    result = local_command([
        str(environment / "bin/python"), "-c",
        "import google.genai, google.cloud.aiplatform, google.cloud.bigquery, google.cloud.firestore, "
        "google.cloud.pubsub_v1, google.cloud.storage, fastapi, uvicorn, pydantic, PIL, dotenv, "
        "multipart, streamlit, requests, pytest, pytest_cov, httpx; print('clean imports PASS')",
    ], cwd=ROOT / "backend")
    assert result.returncode == 0, result.stderr
    assert "clean imports PASS" in result.stdout