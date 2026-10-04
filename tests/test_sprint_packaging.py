import io
import json
import os
import shutil
import subprocess
import tarfile
import uuid
from pathlib import Path

import pytest
from packaging.markers import default_environment
from packaging.requirements import Requirement


def command(arguments, **kwargs):
    return subprocess.run(arguments, capture_output=True, text=True, check=False, **kwargs)


@pytest.fixture(scope="module")
def fresh_image(tmp_path_factory):
    if not shutil.which("docker"):
        pytest.skip("Docker unavailable: image acceptance criteria cannot be certified")
    base = "hotspot-slim:latest"
    available = command(["docker", "image", "inspect", base])
    if available.returncode:
        pytest.skip("Cached runtime image unavailable; no network builds permitted")
    context = tmp_path_factory.mktemp("backend-context")
    backend = Path("backend")
    for filename in ("main.py", "requirements.txt", ".dockerignore"):
        shutil.copyfile(backend / filename, context / filename)
    for package in ("services", "tools"):
        (context / package).mkdir()
        for source in (backend / package).glob("*.py"):
            shutil.copyfile(source, context / package / source.name)
    for filename in ("credentials.json", "qa-key.json", "service-account-qa.json", "qa.pem", "qa.p12"):
        (context / filename).write_text("synthetic QA packaging probe, not a credential")
    for directory in (".venv", ".git", "tests", "data_samples"):
        (context / directory).mkdir()
        (context / directory / "qa-probe").write_text("excluded QA artifact")
    tag = "hotspot-qa-" + uuid.uuid4().hex
    dockerfile = "FROM " + base + "\nWORKDIR /app\nCOPY . .\n"
    environment = dict(os.environ, DOCKER_BUILDKIT="0")
    result = command(["docker", "build", "--network=none", "--pull=false", "-t", tag, "-f", "-", str(context)], input=dockerfile, env=environment)
    assert result.returncode == 0, result.stderr
    try:
        yield tag
    finally:
        command(["docker", "image", "rm", tag])


def test_dockerignore_exists_and_excludes_secrets_environments_and_keys():
    patterns = set(Path("backend/.dockerignore").read_text().splitlines())
    assert {"**/.env", "**/.env.*", "**/.venv/", "**/.git/", "**/*.pem", "**/*.p12", "**/credentials.json", "**/*-key.json", "**/service-account*.json"} <= patterns


def test_dockerfile_is_multistage_non_root_and_honours_injected_port():
    dockerfile = Path("backend/Dockerfile").read_text()
    assert dockerfile.count("FROM ") >= 2, "runtime stage must not carry build tooling"
    assert "USER sentinel" in dockerfile, "container must not run as root"
    assert "uv:latest" not in dockerfile, "mutable uv tag breaks reproducible builds"
    assert "${PORT" in dockerfile, "Cloud Run injects PORT and it must be honoured"
    assert "PYTHONUNBUFFERED=1" in dockerfile
    # Explicit copies keep the stale backend/test_*.py smoke scripts out of the runtime image.
    assert "COPY . ." not in dockerfile


def test_fresh_image_history_and_every_layer_exclude_credentials(fresh_image):
    history = command(["docker", "history", "--no-trunc", fresh_image])
    assert history.returncode == 0
    assert "COPY" in history.stdout
    saved = subprocess.run(["docker", "save", fresh_image], capture_output=True, check=False)
    assert saved.returncode == 0, saved.stderr.decode()
    forbidden = []
    with tarfile.open(fileobj=io.BytesIO(saved.stdout)) as archive:
        for member in archive:
            if not (member.name.endswith("layer.tar") or member.name.startswith("blobs/sha256/")):
                continue
            stream = archive.extractfile(member)
            if stream is None:
                continue
            try:
                with tarfile.open(fileobj=stream, mode="r|*") as layer:
                    for entry in layer:
                        path = Path(entry.name)
                        if "app" not in path.parts:
                            continue
                        if path.name in {"credentials.json", "qa-key.json", "service-account-qa.json", "qa.pem", "qa.p12", ".env"} or set(path.parts) & {".venv", ".git"}:
                            forbidden.append(entry.name)
            except tarfile.ReadError:
                continue
    assert not forbidden, forbidden
    result = command(["docker", "run", "--rm", "--network=none", "--entrypoint", "python", fresh_image, "-c", "from pathlib import Path; assert not any(Path('/app').rglob('qa-probe')); print('artifact exclusion PASS')"])
    assert result.returncode == 0, result.stderr


def test_fresh_image_starts_and_serves_health(fresh_image):
    script = """
import os
from io import StringIO
from unittest.mock import Mock
os.popen = lambda *args, **kwargs: StringIO('')
import google.genai
from google.cloud import bigquery, firestore, pubsub_v1, storage
class DeniedClient:
    def __init__(self, *args, **kwargs):
        raise AssertionError('real cloud client forbidden')
for module, name in [(google.genai, 'Client'), (bigquery, 'Client'), (firestore, 'Client'), (pubsub_v1, 'PublisherClient'), (storage, 'Client')]:
    setattr(module, name, DeniedClient)
import main
clients = {name: Mock() for name in main.DEPENDENCIES}
main.vision_analyzer.get_client = lambda: clients['gemini']
main.database.get_db = lambda: clients['firestore']
main.alert_dispatcher._get_client = lambda: clients['pubsub']
main.climate_service._get_client = lambda: clients['bigquery']
probes = [clients['gemini'].models.get,
          clients['firestore'].collection.return_value.limit.return_value.get,
          clients['pubsub'].get_topic, clients['bigquery'].query]
for probe in probes:
    probe.side_effect = RuntimeError('mock dependency unavailable')
import uvicorn
from fastapi.testclient import TestClient
config = uvicorn.Config('main:app', host='0.0.0.0', port=8080)
config.load()
assert config.loaded_app
with TestClient(main.app) as client:
    response = client.get('/api/live')
    assert response.status_code == 200
    assert response.json() == {'status': 'alive'}
    assert all(not cloud.mock_calls for cloud in clients.values())
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'degraded'
    assert response.json()['dependencies'] == {name: 'unavailable' for name in main.DEPENDENCIES}
    for probe in probes:
        probe.assert_called_once()
print('health HTTP 200')
"""
    result = command(["docker", "run", "--rm", "--network=none", "--entrypoint", "python", fresh_image, "-c", script], timeout=60)
    assert result.returncode == 0, result.stderr
    assert "health HTTP 200" in result.stdout


def dependency_content(text):
    return sorted(str(Requirement(line.strip())) for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#"))


def test_only_one_hand_maintained_manifest_and_backend_is_locked_export():
    result = command(["uv", "export", "--locked", "--offline", "--no-dev", "--no-hashes", "--no-emit-project"])
    assert result.returncode == 0, result.stderr
    backend = Path("backend/requirements.txt").read_text()
    assert "autogenerated by uv" in backend
    assert dependency_content(backend) == dependency_content(result.stdout)
    packages = {Requirement(line).name for line in dependency_content(backend)}
    assert not packages & {"pytest", "pytest-cov"}
    assert not packages & {"streamlit", "altair", "pyarrow"}
    assert "requests" in packages


def test_root_manifest_is_locked_export_with_frontend_and_dev():
    result = command(["uv", "export", "--locked", "--offline", "--group", "frontend", "--group", "dev", "--no-hashes", "--no-emit-project"])
    assert result.returncode == 0, result.stderr
    root = Path("requirements.txt").read_text()
    assert "autogenerated by uv" in root
    assert "uv export --locked --group frontend --group dev --no-hashes --no-emit-project --output-file requirements.txt" in root
    assert dependency_content(root) == dependency_content(result.stdout)
    packages = {Requirement(line).name for line in dependency_content(root)}
    assert {"streamlit", "pytest", "pytest-cov", "requests"} <= packages


def test_image_runtime_versions_match_uv_lock(fresh_image):
    script = "import json,sys; from importlib.metadata import distributions; print(json.dumps({'python': '.'.join(map(str,sys.version_info[:3])), 'packages': {d.metadata['Name'].lower().replace('_','-'): d.version for d in distributions()}}))"
    result = command(["docker", "run", "--rm", "--network=none", "--entrypoint", "python", fresh_image, "-c", script])
    assert result.returncode == 0, result.stderr
    runtime = json.loads(result.stdout)
    environment = default_environment()
    environment.update(python_full_version=runtime["python"], python_version=".".join(runtime["python"].split(".")[:2]), sys_platform="linux", platform_system="Linux")
    for text in dependency_content(Path("backend/requirements.txt").read_text()):
        requirement = Requirement(text)
        if requirement.marker is None or requirement.marker.evaluate(environment):
            name = requirement.name.lower().replace("_", "-")
            assert runtime["packages"].get(name) in requirement.specifier, text
    assert not set(runtime["packages"]) & {"pytest", "pytest-cov"}
    assert not set(runtime["packages"]) & {"streamlit", "altair", "pyarrow"}
    result = command(["docker", "run", "--rm", "--network=none", "--entrypoint", "python", fresh_image, "-c", "import importlib.util; assert importlib.util.find_spec('streamlit') is None; print('streamlit absent PASS')"])
    assert result.returncode == 0, result.stderr
    assert "streamlit absent PASS" in result.stdout