import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import coverage
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/skills/agile-sdlc-loop/scripts/sprint_report.py"


@pytest.fixture
def report_module():
    spec = importlib.util.spec_from_file_location("qa_sprint_report", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_coverage_excludes_only_manual_smoke_scripts_and_keeps_70_percent_floor():
    measured = coverage.Coverage(config_file=str(ROOT / "tests/coverage.ini"))
    assert measured.get_option("run:source") == ["backend"]
    assert measured.get_option("run:omit") == ["backend/test_analyzer.py", "backend/test_pipeline.py"]
    assert measured.get_option("report:fail_under") == 70
    measured._init_for_start()
    for source in (ROOT / "backend").rglob("*.py"):
        if ".venv" in source.parts or "__pycache__" in source.parts:
            continue
        expected = source.name not in {"test_analyzer.py", "test_pipeline.py"}
        assert bool(measured._should_trace(str(source), None).trace) is expected, source


def test_report_runs_pytest_with_visible_application_coverage_config(report_module, monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(command=command, **kwargs)
        return SimpleNamespace(returncode=0, stdout="12 passed in 1.0s\n", stderr="")

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    result = report_module.run_tests()
    assert result["exit_code"] == 0
    assert result["summary"] == "12 passed in 1.0s"
    assert f"--cov-config={ROOT / 'tests/coverage.ini'}" in captured["command"]
    assert "--cov=backend" in captured["command"]
    assert captured["command"][captured["command"].index("-o") + 1] == "addopts="
    assert captured["cwd"] == ROOT


@pytest.mark.parametrize("output,exit_code,reason", [
    ("No module named pytest", 1, "pytest is not installed"),
    ("unrecognized arguments: --cov", 4, "pytest-cov is not installed"),
    ("", 5, "pytest collected no tests"),
])
def test_report_describes_unavailable_test_run(report_module, monkeypatch, output, exit_code, reason):
    monkeypatch.setattr(report_module.subprocess, "run", lambda *args, **kwargs:
                        SimpleNamespace(returncode=exit_code, stdout=output, stderr=""))
    result = report_module.run_tests()
    assert not result["ran"]
    assert reason in result["reason"]


def test_report_handles_test_timeout(report_module, monkeypatch):
    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired("pytest", 900)

    monkeypatch.setattr(report_module.subprocess, "run", timed_out)
    result = report_module.run_tests()
    assert result["ran"] is False
    assert result["reason"] == "test run exceeded 15 minutes"
    assert result["verdict"] == "INCONCLUSIVE"
    assert "pytest" in result["command"]


def test_completed_run_records_verdict_command_and_summary(report_module, monkeypatch):
    monkeypatch.setattr(report_module.subprocess, "run", lambda *args, **kwargs:
                        SimpleNamespace(returncode=0, stdout="607 passed in 60s", stderr=""))
    result = report_module.run_tests()
    assert result["verdict"] == "PASS"
    assert result["summary"] == "607 passed in 60s"
    assert "-m pytest" in result["command"] and "--cov=backend" in result["command"]


def test_timeout_or_missing_result_is_inconclusive_never_pass(report_module, monkeypatch, tmp_path):
    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired("pytest", 900)

    monkeypatch.setattr(report_module.subprocess, "run", timed_out)
    timed = report_module.run_tests()

    monkeypatch.setattr(report_module, "ROOT", tmp_path)
    missing = report_module.run_tests()

    for result in (timed, missing):
        assert report_module.test_verdict(result) == "INCONCLUSIVE"
        assert result["reason"]
        # The recorded command must be runnable as-is so the rerun is deterministic.
        assert result["command"].split()[1:3] == ["-m", "pytest"]


def test_verdict_never_reports_a_run_without_a_result_as_pass(report_module):
    assert report_module.test_verdict({"ran": False, "reason": "interrupted"}) == "INCONCLUSIVE"
    assert report_module.test_verdict({"ran": True, "exit_code": 0}) == "PASS"
    assert report_module.test_verdict({"ran": True, "exit_code": 1}) == "FAIL"


def test_report_handles_missing_tests_directory(report_module, monkeypatch, tmp_path):
    monkeypatch.setattr(report_module, "ROOT", tmp_path)
    assert not report_module.run_tests()["ran"]


def test_report_reads_actual_coverage_totals_and_per_file_values(report_module, monkeypatch, tmp_path):
    artifact = tmp_path / "coverage.json"
    monkeypatch.setattr(report_module, "COVERAGE_JSON", artifact)
    assert report_module.read_coverage() == {}
    artifact.write_text(json.dumps({"totals": {"percent_covered": 95.4321}, "files": {
        "backend/main.py": {"summary": {"percent_covered": 97.654}},
    }}))
    assert report_module.read_coverage() == {"total": 95.4, "files": {"backend/main.py": 97.7}}


@pytest.mark.parametrize("exit_code", [0, 1])
def test_report_no_write_preserves_markdown_and_propagates_suite_verdict(
    report_module, monkeypatch, tmp_path, capsys, exit_code,
):
    backlog = tmp_path / "backlog.json"
    backlog.write_text(json.dumps({"current_sprint": 4, "sprints": [
        {"number": 4, "committed": ["TEST-001"], "goal": "Honest coverage"},
    ], "items": [{"id": "TEST-001", "type": "test", "status": "in_progress",
                  "priority": "P2", "title": "Coverage accounting"}]}))
    reports = tmp_path / "reports"
    monkeypatch.setattr(report_module, "BACKLOG", backlog)
    monkeypatch.setattr(report_module, "REPORTS", reports)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--no-write"])
    monkeypatch.setattr(report_module, "run_tests", lambda: {
        "ran": True, "exit_code": exit_code, "summary": "1 passed" if exit_code == 0 else "1 failed",
    })
    monkeypatch.setattr(report_module, "read_coverage", lambda: {
        "total": 95.4, "files": {"backend/main.py": 95.4},
    })
    assert report_module.main() == exit_code
    assert not reports.exists()
    assert json.loads(backlog.read_text())["items"][0]["status"] == "in_progress"
    output = capsys.readouterr().out
    assert "coverage=95.4" in output
    assert "tests/coverage.ini (backend application code)" in output
    assert "backend/main.py: 95.4%" in output


@pytest.mark.parametrize("tests_result,expected_verdict,unexpected", [
    ({"ran": True, "exit_code": 0, "summary": "607 passed", "command": "python -m pytest tests"},
     "**PASS**", "INCONCLUSIVE"),
    ({"ran": False, "verdict": "INCONCLUSIVE", "reason": "test run exceeded 15 minutes",
      "command": "python -m pytest tests"}, "**INCONCLUSIVE**", "**PASS**"),
])
def test_written_report_records_command_and_never_shows_an_unfinished_run_as_pass(
    report_module, monkeypatch, tmp_path, tests_result, expected_verdict, unexpected,
):
    backlog = tmp_path / "backlog.json"
    backlog.write_text(json.dumps({"current_sprint": 7, "sprints": [
        {"number": 7, "committed": ["TASK-045"], "goal": "Conclusive QA"},
    ], "items": [{"id": "TASK-045", "type": "task", "status": "in_review",
                  "priority": "P1", "title": "Conclusive QA outcomes"}]}))
    reports = tmp_path / "reports"
    monkeypatch.setattr(report_module, "ROOT", tmp_path)
    monkeypatch.setattr(report_module, "COVERAGE_CONFIG", tmp_path / "tests" / "coverage.ini")
    monkeypatch.setattr(report_module, "BACKLOG", backlog)
    monkeypatch.setattr(report_module, "REPORTS", reports)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    monkeypatch.setattr(report_module, "run_tests", lambda: tests_result)
    monkeypatch.setattr(report_module, "read_coverage", lambda: {"total": 90.0, "files": {}})
    report_module.main()

    report = (reports / "sprint-07.md").read_text()
    assert f"- Command: `{tests_result['command']}`" in report
    assert expected_verdict in report
    assert unexpected not in report


def test_application_backend_coverage_meets_recorded_70_percent_floor(report_module):
    artifact = report_module.COVERAGE_JSON
    if not artifact.is_file():
        pytest.skip("Run sprint_report.py to generate the backend coverage artifact")
    data = json.loads(artifact.read_text())
    assert data["totals"]["percent_covered"] >= 70


@pytest.fixture
def coverage_evidence_module():
    spec = importlib.util.spec_from_file_location("qa_coverage_evidence", ROOT / "tests/sprint_coverage_evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def coverage_evidence_inputs():
    def measured(covered):
        return {
            "summary": {"covered_lines": covered, "num_statements": 100,
                        "percent_covered": 50, "num_branches": 20, "covered_branches": 10},
            "missing_lines": [10], "missing_branches": [[10, 11]],
        }

    backend = {"files": {"backend/main.py": measured(95)}}
    components = {"files": {
        "frontend/app.py": measured(80),
        ".github/skills/heat-report-validation/scripts/validate_report.py": measured(70),
    }}
    backlog = {"current_sprint": 5, "items": []}
    historical = {"files": {
        "frontend/app.py": {"summary": {"num_statements": 90}},
        ".github/skills/heat-report-validation/scripts/validate_report.py": {
            "summary": {"num_statements": 94},
        },
    }}
    return backend, components, backlog, historical


def test_sprint_metrics_report_separate_statement_deltas_and_missing_branches(
    coverage_evidence_module, coverage_evidence_inputs,
):
    evidence = coverage_evidence_module.build_evidence(*coverage_evidence_inputs)
    groups = evidence["groups"]
    assert groups["backend"]["statement_percent"] == 95.0
    assert groups["backend"]["delta_percentage_points"] == -3.3
    assert groups["frontend"]["delta_percentage_points"] == -3.3
    assert groups["validator"]["delta_percentage_points"] == -8.7
    assert list(groups["backend"]["files"]) == ["backend/main.py"]
    assert list(groups["frontend"]["files"]) == ["frontend/app.py"]
    assert list(groups["validator"]["files"]) == [
        ".github/skills/heat-report-validation/scripts/validate_report.py",
    ]
    for group in groups.values():
        metric = next(iter(group["files"].values()))
        assert metric["missing_lines"] == [10]
        assert metric["missing_branches"] == [[10, 11]]
        assert metric["branch_percent"] == 50.0
    assert evidence["followups_for_orchestrator"] == []


def test_sprint_metrics_explain_changed_and_unknown_historical_denominators(
    coverage_evidence_module, coverage_evidence_inputs,
):
    groups = coverage_evidence_module.build_evidence(*coverage_evidence_inputs)["groups"]
    assert groups["frontend"]["denominator_delta"] == 10
    assert groups["validator"]["denominator_delta"] == 6
    assert groups["backend"]["historical_statement_denominator"] is None
    assert groups["backend"]["denominator_delta"] is None
    assert "no like-for-like count claimed" in groups["backend"]["denominator_note"]


@pytest.mark.parametrize("path", ["backend/test_analyzer.py", "backend/test_pipeline.py", "frontend/app.py"])
def test_sprint_metrics_reject_manual_smoke_or_frontend_in_backend_denominator(
    coverage_evidence_module, coverage_evidence_inputs, path,
):
    backend, components, backlog, historical = coverage_evidence_inputs
    backend["files"][path] = backend["files"]["backend/main.py"]
    with pytest.raises(ValueError, match="non-application"):
        coverage_evidence_module.build_evidence(backend, components, backlog, historical)


@pytest.mark.parametrize("has_existing_task", [False, True], ids=["propose-test-task", "reuse-test-task"])
def test_below_floor_metrics_route_reproducible_test_followups_without_backlog_writes(
    coverage_evidence_module, coverage_evidence_inputs, has_existing_task,
):
    backend, components, backlog, historical = coverage_evidence_inputs
    components["files"]["frontend/app.py"]["summary"]["covered_lines"] = 69
    if has_existing_task:
        backlog["items"].append({
            "id": "TEST-QA", "type": "test", "status": "in_progress", "files": ["frontend/app.py"],
        })
    original = json.dumps(backlog, sort_keys=True)
    evidence = coverage_evidence_module.build_evidence(backend, components, backlog, historical)
    assert json.dumps(backlog, sort_keys=True) == original
    assert len(evidence["followups_for_orchestrator"]) == 1
    followup = evidence["followups_for_orchestrator"][0]
    assert followup["file"] == "frontend/app.py"
    assert followup["existing_ids"] == (["TEST-QA"] if has_existing_task else [])
    if has_existing_task:
        assert followup["proposal"] is None
    else:
        proposal = followup["proposal"]
        assert proposal["type"] == "test"
        assert proposal["priority"] == "P2"
        assert "Expected at least 70%" in proposal["description"]
        assert "actual 69.0%" in proposal["description"]
        assert "Missing lines: [10]" in proposal["description"]


def test_coverage_floor_cannot_be_evaded_by_rounding_up_to_70_percent(
    coverage_evidence_module, coverage_evidence_inputs,
):
    backend, components, backlog, historical = coverage_evidence_inputs
    summary = components["files"]["frontend/app.py"]["summary"]
    summary.update(covered_lines=6996, num_statements=10000)
    evidence = coverage_evidence_module.build_evidence(backend, components, backlog, historical)
    assert evidence["groups"]["frontend"]["statement_percent"] == 70.0
    assert len(evidence["followups_for_orchestrator"]) == 1


def test_existing_report_lists_per_file_coverage_and_flags_below_floor(report_module):
    rendered = "\n".join(report_module.coverage_lines({
        "total": 70.0, "files": {"backend/main.py": 69.0, "backend/services/database.py": 70.0},
    }))
    assert "| backend/main.py | 69.0% |" in rendered
    assert "| backend/services/database.py | 70.0% |" in rendered
    assert "Below the 70% floor" in rendered
    assert "- backend/main.py" in rendered
    assert "- backend/services/database.py" not in rendered


def test_regression_evidence_records_pass_failure_and_skip_from_junit(coverage_evidence_module, tmp_path):
    artifact = tmp_path / "junit.xml"
    assert not coverage_evidence_module.regression_evidence(artifact)["available"]
    artifact.write_text(
        '<testsuites><testsuite>'
        '<testcase classname="tests.test_contract" name="test_valid_contract" />'
        '<testcase classname="tests.test_contract" name="test_invalid_contract"><failure /></testcase>'
        '<testcase classname="tests.test_frontend" name="test_unavailable"><skipped /></testcase>'
        '<testcase classname="tests.test_foundation" name="test_other" />'
        '</testsuite></testsuites>'
    )
    evidence = coverage_evidence_module.regression_evidence(artifact)
    assert evidence["available"]
    assert evidence["modules"] == {
        "tests.test_contract": [
            {"name": "test_valid_contract", "status": "passed"},
            {"name": "test_invalid_contract", "status": "failed"},
        ],
        "tests.test_frontend": [{"name": "test_unavailable", "status": "skipped"}],
    }


def test_sprint_metrics_cli_writes_only_json_evidence_and_preserves_backlog(
    coverage_evidence_module, coverage_evidence_inputs, monkeypatch, tmp_path, capsys,
):
    backend, components, backlog, historical = coverage_evidence_inputs
    (tmp_path / "agile").mkdir()
    (tmp_path / "tests").mkdir()
    paths = {
        "backend.json": backend, "components.json": components,
        "agile/backlog.json": backlog, "tests/sprint4_coverage.json": historical,
    }
    for path, contents in paths.items():
        (tmp_path / path).write_text(json.dumps(contents))
    original = (tmp_path / "agile/backlog.json").read_bytes()
    monkeypatch.setattr(coverage_evidence_module, "ROOT", tmp_path)
    output = tmp_path / "tests/metrics.json"
    assert coverage_evidence_module.main([
        "--backend", str(tmp_path / "backend.json"),
        "--components", str(tmp_path / "components.json"), "--output", str(output),
    ]) == 0
    evidence = json.loads(output.read_text())
    assert evidence["sprint"] == 5
    assert evidence["groups"]["backend"]["delta_percentage_points"] == -3.3
    assert (tmp_path / "agile/backlog.json").read_bytes() == original
    assert not list(tmp_path.rglob("*.md"))
    assert "backend: 95.0% (-3.3 pp)" in capsys.readouterr().out