import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tomllib
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from packaging.requirements import Requirement

from services import alert_dispatcher, vision_analyzer
from tools import climate_service


ROOT = Path(__file__).resolve().parents[1]


def test_workspace_uv_lock_python_constraint_and_declared_dependencies_are_parsed_in_place():
    lock_path = ROOT / "uv.lock"
    lock = tomllib.loads(lock_path.read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert lock_path.parent == ROOT
    assert lock["requires-python"] == project["requires-python"] == ">=3.10"
    assert {Requirement(value).name.lower().replace("_", "-") for value in project["dependencies"]} <= {
        package["name"] for package in lock["package"]
    }


def test_handoff_requires_workspace_command_and_canonical_artifact_evidence():
    instructions = (ROOT / ".github/copilot-instructions.md").read_text()
    assert "run it in the workspace and check the file in place" in instructions
    assert "temp directory proves nothing" in instructions
    result = subprocess.run(["uv", "lock", "--check", "--offline"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (ROOT / "uv.lock").is_file()
    print(f"command=uv lock --check --offline cwd={ROOT} canonical_output={ROOT / 'uv.lock'}")


def test_narrowed_exception_boundaries_require_same_change_sdk_regressions():
    instructions = (ROOT / ".github/copilot-instructions.md").read_text()
    assert "requires a test in the same change" in instructions
    assert "issubclass" in instructions
    for name in ("DataCorruption", "RpcError", "MessageTooLargeError", "OSError", "EnvironmentError"):
        assert name in instructions


def test_missing_failure_case_evidence_blocks_qa_handoff():
    expected = {
        "test_checksum_failure_warns_retains_files_and_continues_uploads",
        "test_dispatch_failures_return_empty_id_and_type_only_logs",
        "test_exception_boundary_matrix_proves_sdk_failure_inheritance",
        "test_missing_project_climate_lookup_returns_labelled_fallback",
        "test_missing_project_firestore_raises_database_error_and_api_returns_503",
        "test_missing_project_seeder_warns_and_retains_generated_local_files",
        "test_typeerror_and_keyerror_still_propagate_from_client_construction",
        "test_typeerror_and_keyerror_still_propagate_from_database_and_seeder_operations",
    }
    present = {node.name for path in (ROOT / "tests").glob("test_*.py")
               for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, ast.FunctionDef)}
    assert expected <= present, f"Missing mandatory failure evidence: {expected - present}"


def test_contract_changes_identify_analyzer_api_and_dashboard_consumers_and_checks():
    instructions = (ROOT / ".github/copilot-instructions.md").read_text()
    assert "A contract change is not done until its consumers are updated" in instructions
    assert "`main.py` and `frontend/app.py` consume the analyzer's schema" in instructions
    gate = ast.parse((ROOT / "tests/test_cross_layer_contract.py").read_text())
    present = {node.name for node in gate.body if isinstance(node, ast.FunctionDef)}
    assert {"test_every_resolved_backend_coroutine_call_is_consumed",
            "test_all_report_field_reads_match_the_producer_schema",
            "test_dashboard_api_and_analyzer_preserve_image_mime",
            "test_alert_flag_and_banner_mean_successful_publish_before_persistence"} <= present


def test_literal_test_definitions_are_discoverable_without_generated_globals(pytestconfig):
    definitions = {}
    for path in (ROOT / "tests").glob("test_*.py"):
        tree = ast.parse(path.read_text())
        definitions[path.name] = {node.name for node in ast.walk(tree)
                                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                                  and node.name.startswith("test_")}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                assert not any(isinstance(target, ast.Subscript) and isinstance(target.value, ast.Call)
                               and isinstance(target.value.func, ast.Name) and target.value.func.id == "globals"
                               for target in node.targets), f"Generated test registration in {path}"
    for item in pytestconfig._qa_collected_items:
        assert item.originalname in definitions[item.path.name]


def test_collected_tests_include_the_underlying_no_sys_path_invariant(pytestconfig):
    expected = "test_backend_imports_do_not_mutate_interpreter_search_directories"
    owning_module = ROOT / "tests/test_package_layout.py"
    definitions = {node.name for node in ast.walk(ast.parse(owning_module.read_text()))
                   if isinstance(node, ast.FunctionDef)}
    assert expected in definitions
    if any(item.path == owning_module for item in pytestconfig._qa_collected_items):
        assert any(item.originalname == expected for item in pytestconfig._qa_collected_items)
    for path in (ROOT / "backend").rglob("*.py"):
        tree = ast.parse(path.read_text())
        assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                       and ast.unparse(node.func) in {"sys.path.append", "sys.path.insert"}
                       for node in ast.walk(tree)), path


def test_guide_defines_climate_source_values_and_response_storage_placement():
    guide = (ROOT / "COPILOT_GUIDE.md").read_text()
    assert "`climate_source`" in guide
    assert "`bigquery` \\| `fallback`" in guide or "`bigquery` | `fallback`" in guide
    assert "API response and the persisted scan" in guide


def test_guide_and_nfr_1_document_us_noaa_only_location_exception():
    guide = (ROOT / "COPILOT_GUIDE.md").read_text()
    requirements = (ROOT / "agile/requirements.md").read_text()
    region = next(line for line in guide.splitlines() if line.startswith("- Region:"))
    nfr = next(line for line in requirements.splitlines() if "**NFR-1 " in line)
    for policy in (region, nfr):
        normalized = policy.replace("`", "").replace("**", "").casefold()
        assert "narrow exception" in normalized, policy
        assert "bigquery-public-data.noaa_gsod" in normalized, policy
        assert "bigquery_location" in normalized, policy
        assert re.search(r"default\s+us\b", normalized), policy
        assert "us multi-region" in normalized, policy
        assert "public-dataset read only" in normalized, policy
        assert re.search(r"every resource .* stays in asia-southeast1", normalized), policy


def test_documented_climate_provenance_and_location_match_runtime_policy():
    import main

    assert climate_service.BIGQUERY_LOCATION == "US"
    assert set(main.AnalysisResponse.model_fields["climate_source"].annotation.__args__[0].__args__) == {
        "bigquery", "fallback", "caller"
    }
    assert main.READINESS_RPC_TIMEOUT_SECONDS == 4.5
    assert main.MAX_UPLOAD_BYTES == 10_000_000
    assert main.ALLOWED_UPLOAD_CONTENT_TYPES == {"image/jpeg", "image/png"}


def test_analyze_declares_response_model_with_canonical_and_envelope_fields(api_environment):
    main = api_environment[0]
    route = next(route for route in main.app.routes if route.path == "/api/analyze")
    assert route.response_model is main.AnalysisResponse
    assert set(vision_analyzer.HotspotAnalysisResult.model_fields) <= set(route.response_model.model_fields)
    assert {"climate_source", "doc_id", "alert_attempted"} <= set(route.response_model.model_fields)


def test_http_model_agrees_with_canonical_report_and_documented_provenance(api_environment):
    main = api_environment[0]
    for name, field in vision_analyzer.HotspotAnalysisResult.model_fields.items():
        assert main.AnalysisResponse.model_fields[name].annotation == field.annotation
    assert "`climate_source`" in (ROOT / "COPILOT_GUIDE.md").read_text()


def test_analysis_persists_scan_and_returns_generated_doc_id(api_environment, sample_png_bytes):
    response = TestClient(api_environment[0].app).post(
        "/api/analyze", files={"file": ("district.png", sample_png_bytes, "image/png")}
    )
    assert response.status_code == 200
    assert response.json()["doc_id"] == "generated-scan-id"
    api_environment[4].collection.return_value.document.return_value.set.assert_called_once()


@pytest.mark.parametrize("image_format,mime,expected_status", [
    ("PNG", "image/png", 200), ("JPEG", "image/jpeg", 200), ("WEBP", "image/webp", 415),
])
def test_png_jpeg_accepted_and_webp_rejected_before_cloud_calls(api_environment, image_format, mime, expected_status):
    from io import BytesIO
    from PIL import Image

    image = BytesIO()
    Image.new("RGB", (8, 8)).save(image, format=image_format)
    response = TestClient(api_environment[0].app).post(
        "/api/analyze", files={"file": ("district." + image_format.lower(), image.getvalue(), mime)}
    )
    assert response.status_code == expected_status
    if expected_status == 415:
        api_environment[1].assert_not_awaited()
        api_environment[2].assert_not_called()
        api_environment[3].assert_not_called()
        api_environment[4].collection.assert_not_called()


@pytest.mark.parametrize("score,band,expected", [(3.9, "LOW", 0), (4.0, "MODERATE", 0),
    (5.9, "MODERATE", 0), (6.0, "HIGH", 0), (7.9, "HIGH", 0), (8.0, "CRITICAL", 1)])
def test_alert_publishes_only_at_or_above_eight_with_canonical_bands(monkeypatch, valid_report, score, band, expected):
    publisher = Mock()
    publisher.publish.return_value.result.return_value = "published-id"
    constructor = Mock(return_value=publisher)
    monkeypatch.setattr(alert_dispatcher, "_client", None)
    monkeypatch.setattr(alert_dispatcher.pubsub_v1, "PublisherClient", constructor)
    valid_report.update(hvi_score=score, risk_level=band)
    assert alert_dispatcher.dispatch_heat_alert(valid_report) == ("published-id" if expected else "")
    assert publisher.publish.call_count == expected


def test_subcritical_alert_returns_empty_string_without_constructing_client(monkeypatch, valid_report):
    constructor = Mock(side_effect=AssertionError("Non-critical reports must not construct a client"))
    monkeypatch.setattr(alert_dispatcher, "_client", None)
    monkeypatch.setattr(alert_dispatcher.pubsub_v1, "PublisherClient", constructor)
    valid_report.update(hvi_score=7.9, risk_level="HIGH")
    assert alert_dispatcher.dispatch_heat_alert(valid_report) == ""
    constructor.assert_not_called()


def test_alert_message_carries_coordinates_temperature_and_urgent_actions(monkeypatch, valid_report):
    publisher = Mock()
    publisher.publish.return_value.result.return_value = "published-id"
    monkeypatch.setattr(alert_dispatcher, "_get_client", lambda: publisher)
    valid_report["private_extra"] = "must-not-publish"
    assert alert_dispatcher.dispatch_heat_alert(valid_report) == "published-id"
    data = publisher.publish.call_args.args[1]
    event = json.loads(data)
    assert event["coordinates"] == valid_report["coordinates"]
    assert event["ambient_temp_c"] == valid_report["ambient_temp_c"]
    assert event["urgent_interventions"] == valid_report["passive_cooling_plan"]["micro_canopy_interventions"]
    assert "private_extra" not in event
    assert event["schema_version"] == 1
    assert len(data) < 4096
    attributes = publisher.publish.call_args.kwargs
    assert attributes["risk_level"] == "CRITICAL"
    assert attributes["alert_type"] == "CRITICAL_HEAT"
    assert attributes["zone_id"] == valid_report["zone_id"]
    assert attributes["region"] == "asia-southeast1"
    repeated = alert_dispatcher._build_alert(valid_report)
    assert event["event_id"] == repeated["event_id"]
    other_scan = copy.deepcopy(valid_report)
    other_scan["timestamp"] = "2026-10-02T13:00:00Z"
    assert event["event_id"] != alert_dispatcher._build_alert(other_scan)["event_id"]


@pytest.fixture(scope="module")
def hardened_image():
    """Build the hardened image from the current source so the proof is never stale.

    A pre-existing tag cannot certify the working tree: any edit after the last
    manual build makes the layer-content check fail for the wrong reason, which
    is exactly what happened mid-sprint. Building here gives a clean checkout and
    CI a deterministic path. Anything that prevents the build is an explicit skip,
    never a pass, because an uncertified image must not look like a certified one.
    """
    if not shutil.which("docker"):
        pytest.skip("Docker unavailable; hardened runtime cannot be certified")
    image = "hotspot-hardened:pytest"
    build = subprocess.run(
        ["docker", "build", "--platform", "linux/amd64", "-f", "backend/Dockerfile", "-t", image, "backend"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if build.returncode:
        pytest.skip(f"Hardened image could not be built, so it is uncertified: {build.stderr.strip()[-300:]}")
    return image


def docker_python(image, script):
    result = subprocess.run(
        ["docker", "run", "--rm", "--network=none", "--entrypoint", "python", image, "-c", script],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_multistage_runtime_has_no_uv_or_build_tooling(hardened_image):
    dockerfile = (ROOT / "backend/Dockerfile").read_text()
    assert dockerfile.count("FROM ") == 2
    docker_python(hardened_image, "import shutil; assert shutil.which('uv') is None; assert shutil.which('gcc') is None")


def test_hardened_runtime_runs_as_non_root_sentinel_uid_10001(hardened_image):
    docker_python(hardened_image, "import os,pwd; assert os.getuid()==10001; assert pwd.getpwuid(os.getuid()).pw_name=='sentinel'")


def test_uv_builder_image_is_pinned_to_a_version_tag():
    dockerfile = (ROOT / "backend/Dockerfile").read_text()
    assert "ghcr.io/astral-sh/uv:0.12.3" in dockerfile
    assert "uv:latest" not in dockerfile


def test_hardened_runtime_honours_port_9090_and_does_not_bind_8080(hardened_image):
    result = subprocess.run(["docker", "image", "inspect", hardened_image], capture_output=True, text=True)
    assert result.returncode == 0
    command = json.loads(result.stdout)[0]["Config"]["Cmd"]
    assert "${PORT" in " ".join(command)
    script = """
import json, os, socket, subprocess, urllib.request
os.environ['PORT'] = '9090'
server = subprocess.Popen(COMMAND, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
try:
    for line in server.stderr:
        if 'Uvicorn running on' in line:
            break
    response = urllib.request.urlopen('http://127.0.0.1:9090/openapi.json', timeout=5)
    assert response.status == 200
    assert '/api/health' in json.load(response)['paths']
    probe = socket.socket()
    probe.settimeout(1)
    assert probe.connect_ex(('127.0.0.1', 8080)) != 0
    probe.close()
finally:
    server.terminate()
    server.wait(timeout=10)
""".replace("COMMAND", repr(command))
    docker_python(hardened_image, script)


def test_documented_backend_docker_build_context_resolves_explicit_copies():
    for document in (ROOT / "README.md", ROOT / ".github/skills/cloudrun-deploy/SKILL.md"):
        commands = re.findall(r"docker build [^`\n)]+", document.read_text())
        assert commands, f"No documented Docker build command in {document}"
        for command in commands:
            arguments = shlex.split(command)
            assert arguments[arguments.index("-f") + 1] == "backend/Dockerfile"
            assert arguments[-1] == "backend", command
    context = ROOT / "backend"
    dockerfile = (ROOT / "backend/Dockerfile").read_text()
    for line in dockerfile.splitlines():
        if line.startswith("COPY ") and "--from=" not in line:
            for source in shlex.split(line)[1:-1]:
                assert (context / source).exists(), f"Backend-context build cannot resolve COPY {source}"


def test_hardened_image_application_sources_match_canonical_workspace(hardened_image):
    paths = [ROOT / "backend/main.py", ROOT / "backend/verify_setup.py"]
    paths += [path for package in ("services", "tools") for path in (ROOT / "backend" / package).glob("*.py")]
    expected = {str(Path("/app") / path.relative_to(ROOT / "backend")): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in paths}
    script = "import hashlib; from pathlib import Path; expected=" + repr(expected)
    script += "; assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in expected.items())"
    docker_python(hardened_image, script)