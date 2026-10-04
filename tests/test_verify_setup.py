import os
import runpy
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import dotenv
from google import genai

SCRIPT = Path(__file__).resolve().parents[1] / "backend/verify_setup.py"


@pytest.fixture
def verify_client(monkeypatch):
    monkeypatch.setattr(dotenv, "load_dotenv", MagicMock(return_value=False))
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "offline-test-project")
    client = MagicMock()
    client.models.generate_content.return_value.text = "HotSpot Sentinels environment operational."
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr(genai, "Client", constructor)
    return constructor, client


@pytest.mark.parametrize("use_defaults", [False, True])
def test_verify_setup_reads_env_not_gcloud(monkeypatch, verify_client, use_defaults):
    def reject_shell(*args, **kwargs):
        raise AssertionError("verify_setup must not shell out")

    monkeypatch.setattr(os, "popen", reject_shell)
    monkeypatch.setattr(subprocess, "Popen", reject_shell)
    if not use_defaults:
        monkeypatch.setenv("GOOGLE_CLOUD_REGION", "qa-region")
        monkeypatch.setenv("MODEL_ID", "qa-model")
    constructor, client = verify_client
    namespace = runpy.run_path(str(SCRIPT))
    constructor.assert_not_called()
    loader = MagicMock(return_value=False)
    monkeypatch.setitem(namespace["main"].__globals__, "load_dotenv", loader)
    assert namespace["main"]() == 0
    loader.assert_called_once_with()
    constructor.assert_called_once()
    arguments = constructor.call_args.kwargs
    assert arguments["vertexai"] is True
    assert arguments["project"] == "offline-test-project"
    assert arguments["location"] == ("asia-southeast1" if use_defaults else "qa-region")
    assert client.models.generate_content.call_args.kwargs["model"] == (
        "gemini-2.5-flash" if use_defaults else "qa-model"
    )


def test_verify_setup_exits_nonzero_on_api_error(verify_client, capsys):
    verify_client[1].models.generate_content.side_effect = RuntimeError("RAW_CLOUD_PAYLOAD")
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert error.value.code != 0
    output = capsys.readouterr().out
    assert output.strip() == "[ERROR] Vertex AI connectivity check failed."


def test_verify_setup_exits_zero_on_success(verify_client, capsys):
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert error.value.code == 0
    assert "HotSpot Sentinels environment operational." in capsys.readouterr().out


# AC1 requires printing the reply; AC5 protects our credentials and raw errors.
# A fixed prompt cannot expose our secrets through a reply; test its bound separately.
@pytest.mark.parametrize("outcome", ["success", "api_error"])
def test_verify_setup_does_not_print_credentials(verify_client, capsys, outcome):
    token = "ya29.QA_ONLY_FAKE_TOKEN"
    raw = f"RAW_CLOUD_PAYLOAD projects/private-project Bearer {token}"
    if outcome == "api_error":
        verify_client[1].models.generate_content.side_effect = RuntimeError(raw)
    with pytest.raises(SystemExit):
        runpy.run_path(str(SCRIPT), run_name="__main__")
    captured = capsys.readouterr()
    output = captured.out + captured.err
    for sensitive in (token, "Bearer", "RAW_CLOUD_PAYLOAD", "private-project", "Traceback"):
        assert sensitive not in output


def test_verify_setup_prints_reply_as_one_bounded_line(verify_client, capsys):
    reply = "  operational\n\tready\r\n" * 1000
    verify_client[1].models.generate_content.return_value.text = reply
    namespace = runpy.run_path(str(SCRIPT))
    assert namespace["main"]() == 0
    captured = capsys.readouterr()
    prefix = "[SUCCESS] Vertex AI Response: "
    lines = captured.out.splitlines()
    assert len(lines) == 1
    assert lines[0] == prefix + " ".join(reply.split())[:namespace["MAX_REPLY_CHARS"]]
    assert len(lines[0]) <= len(prefix) + namespace["MAX_REPLY_CHARS"]
    assert captured.err == ""


@pytest.mark.parametrize("reply", [None, "", "   "])
def test_verify_setup_exits_nonzero_on_empty_reply(verify_client, reply):
    verify_client[1].models.generate_content.return_value.text = reply
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert error.value.code != 0


def test_verify_setup_exits_nonzero_without_project(monkeypatch, verify_client):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT")
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert error.value.code != 0
    verify_client[0].assert_not_called()