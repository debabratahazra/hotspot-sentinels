import importlib
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from google.api_core.exceptions import ServiceUnavailable
from google.auth.exceptions import DefaultCredentialsError
from google.cloud.storage.exceptions import DataCorruption
from PIL import Image

from tools import seed_samples


@pytest.fixture
def sample_directory(monkeypatch, tmp_path):
    destination = tmp_path / "data_samples"
    monkeypatch.setattr(seed_samples, "DATA_DIR", destination)
    monkeypatch.setattr(seed_samples, "_client", None)
    return destination


@pytest.fixture
def fake_storage(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "offline-test-project")
    monkeypatch.setenv("GCS_BUCKET_NAME", "offline-test-bucket")
    client = MagicMock()
    bucket = client.bucket.return_value
    blobs = {}

    def get_blob(name):
        if name not in blobs:
            blobs[name] = MagicMock()
            blobs[name].name = name
        return blobs[name]

    bucket.blob.side_effect = get_blob
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr(seed_samples.storage, "Client", constructor)
    return constructor, client, blobs


def test_three_distinguishable_scenes_are_written(sample_directory):
    paths = seed_samples.generate_samples()
    assert {path.name for path in paths} == {
        "industrial_hotspot.jpg", "mixed_residential.jpg", "cool_park.jpg"
    }
    assert set(sample_directory.iterdir()) == set(paths)
    pixels = []
    for path in paths:
        with Image.open(path) as image:
            assert image.mode == "RGB"
            assert image.size == (1024, 1024)
            pixels.append(image.tobytes())
    assert len(set(pixels)) == 3


def test_bare_seed_samples_import_creates_nothing(monkeypatch, tmp_path):
    def reject_write(*args, **kwargs):
        raise AssertionError("Import must not create images or directories")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "mkdir", reject_write)
    monkeypatch.setattr(Image.Image, "save", reject_write)
    monkeypatch.delitem(sys.modules, "tools.seed_samples", raising=False)
    module = importlib.import_module("tools.seed_samples")
    assert module._client is None
    assert list(tmp_path.iterdir()) == []
    monkeypatch.setitem(sys.modules, "tools.seed_samples", seed_samples)


def test_unset_bucket_warns_skips_uploads_and_writes_local_files(sample_directory, caplog, capsys):
    with caplog.at_level(logging.WARNING):
        seed_samples.main()
    assert len(list(sample_directory.glob("*.jpg"))) == 3
    assert seed_samples._client is None
    assert "GCS_BUCKET_NAME is unset" in caplog.text
    assert "3 written, 0 uploaded, 3 uploads skipped" in capsys.readouterr().out


def test_three_blobs_upload_under_samples_prefix(sample_directory, fake_storage):
    paths = seed_samples.generate_samples()
    uploaded = seed_samples.upload_samples(paths)
    constructor, client, blobs = fake_storage
    constructor.assert_called_once()
    assert constructor.call_args.kwargs["project"] == "offline-test-project"
    client.bucket.assert_called_once_with("offline-test-bucket")
    assert set(blobs) == {f"samples/{path.name}" for path in paths}
    assert uploaded == [f"gs://offline-test-bucket/samples/{path.name}" for path in paths]
    for path in paths:
        upload_call = blobs[f"samples/{path.name}"].upload_from_filename
        upload_call.assert_called_once()
        assert upload_call.call_args.args[0] == str(path)
        assert upload_call.call_args.kwargs["content_type"] == "image/jpeg"
        assert upload_call.call_args.kwargs["timeout"] == 30
    assert seed_samples._get_client() is client
    constructor.assert_called_once()


def test_upload_failure_warns_and_continues(sample_directory, fake_storage, caplog):
    paths = seed_samples.generate_samples()
    constructor, client, blobs = fake_storage
    failing_blob = client.bucket.return_value.blob(f"samples/{paths[0].name}")
    failing_blob.upload_from_filename.side_effect = ServiceUnavailable("RAW_CLOUD_PAYLOAD")
    with caplog.at_level(logging.WARNING):
        uploaded = seed_samples.upload_samples(paths)
    assert len(uploaded) == 2
    assert all(path.exists() for path in paths)
    assert "upload failed" in caplog.text
    assert "RAW_CLOUD_PAYLOAD" not in caplog.text
    assert all(blob.upload_from_filename.call_count == 1 for blob in blobs.values())


def test_missing_credentials_warn_and_retain_local_files(sample_directory, fake_storage, caplog):
    paths = seed_samples.generate_samples()
    fake_storage[0].side_effect = DefaultCredentialsError("RAW_CLOUD_PAYLOAD")
    with caplog.at_level(logging.WARNING):
        assert seed_samples.upload_samples(paths) == []
    assert all(path.exists() for path in paths)
    assert "storage client unavailable" in caplog.text
    assert "RAW_CLOUD_PAYLOAD" not in caplog.text


def test_cloud_errors_explicitly_includes_data_corruption():
    assert DataCorruption in seed_samples.CLOUD_ERRORS


@pytest.mark.parametrize("entrypoint", ["upload_samples", "main"])
def test_checksum_failure_warns_retains_files_and_continues_uploads(
    entrypoint, sample_directory, fake_storage, caplog, capsys
):
    constructor, client, blobs = fake_storage
    filenames = ["industrial_hotspot.jpg", "mixed_residential.jpg", "cool_park.jpg"]
    failed_filename = filenames[0]
    failing_blob = client.bucket.return_value.blob(f"samples/{failed_filename}")
    failing_blob.upload_from_filename.side_effect = DataCorruption(None, "RAW_SDK_CHECKSUM_PAYLOAD")
    expected_uploads = [
        f"gs://offline-test-bucket/samples/{filename}" for filename in filenames[1:]
    ]

    with caplog.at_level(logging.WARNING, logger=seed_samples.__name__):
        if entrypoint == "upload_samples":
            paths = seed_samples.generate_samples()
            original_contents = {path: path.read_bytes() for path in paths}
            assert seed_samples.upload_samples(paths) == expected_uploads
            assert {path: path.read_bytes() for path in paths} == original_contents
        else:
            assert seed_samples.main() is None

    assert {path.name for path in sample_directory.iterdir()} == set(filenames)
    for filename in filenames:
        path = sample_directory / filename
        with Image.open(path) as image:
            assert image.format == "JPEG"
            assert image.size == (1024, 1024)
            image.verify()
        upload_call = blobs[f"samples/{filename}"].upload_from_filename
        upload_call.assert_called_once()
        assert upload_call.call_args.args[0] == str(path)
        assert upload_call.call_args.kwargs["content_type"] == "image/jpeg"
        assert upload_call.call_args.kwargs["timeout"] == 30
    assert set(blobs) == {f"samples/{filename}" for filename in filenames}
    constructor.assert_called_once()
    assert constructor.call_args.kwargs["project"] == "offline-test-project"

    warnings = [record for record in caplog.records if record.name == seed_samples.__name__]
    assert len(warnings) == 1
    warning = warnings[0]
    assert warning.levelno == logging.WARNING
    assert warning.getMessage() == (
        f"Skipped GCS upload for {failed_filename}: upload failed (DataCorruption); "
        "local file retained."
    )
    assert warning.exc_info is None
    assert warning.exc_text is None
    assert warning.stack_info is None
    output = capsys.readouterr()
    assert "RAW_SDK_CHECKSUM_PAYLOAD" not in caplog.text + output.out + output.err
    assert "Traceback" not in caplog.text + output.out + output.err
    if entrypoint == "main":
        assert "3 written, 2 uploaded, 1 uploads skipped" in output.out
        assert output.out.count("Uploaded: ") == 2
        for uri in expected_uploads:
            assert f"Uploaded: {uri}" in output.out
        assert f"Uploaded: gs://offline-test-bucket/samples/{failed_filename}" not in output.out


def test_seed_main_reports_successful_uploads(sample_directory, fake_storage, capsys):
    seed_samples.main()
    output = capsys.readouterr().out
    assert output.count("Uploaded: gs://offline-test-bucket/samples/") == 3
    assert "3 written, 3 uploaded, 0 uploads skipped" in output