"""Supplement the existing sprint report with separate, comparable QA metrics."""

import argparse
import json
import xml.etree.ElementTree as ElementTree
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINES = {"backend": 98.3, "frontend": 83.3, "validator": 78.7}
COMPONENT_PATHS = {
    "frontend": "frontend/app.py",
    "validator": ".github/skills/heat-report-validation/scripts/validate_report.py",
}
MANUAL_SCRIPTS = {"backend/test_analyzer.py", "backend/test_pipeline.py"}


def regression_evidence(junit_path):
    if not junit_path.is_file():
        return {"available": False, "reason": "Run sprint_report.py --no-write to produce JUnit evidence."}
    cases = ElementTree.parse(junit_path).getroot().iter("testcase")
    modules = {}
    for case in cases:
        module = case.get("classname", "")
        if module not in {"tests.test_dashboard_coverage", "tests.test_frontend", "tests.test_contract",
                          "tests.test_api", "tests.test_vision_analyzer", "tests.test_sprint_report"}:
            continue
        status = "passed"
        if case.find("failure") is not None or case.find("error") is not None:
            status = "failed"
        elif case.find("skipped") is not None:
            status = "skipped"
        modules.setdefault(module, []).append({"name": case.get("name"), "status": status})
    return {"available": True, "modules": modules}


def file_metric(info):
    summary = info["summary"]
    statements = summary["num_statements"]
    covered = summary["covered_lines"]
    percent = round(100 * covered / statements, 1) if statements else 100.0
    branches = summary.get("num_branches")
    return {
        "statement_percent": percent,
        "covered_statements": covered,
        "statement_denominator": statements,
        "missing_lines": info.get("missing_lines", []),
        "branch_percent": (
            round(100 * summary["covered_branches"] / branches, 1) if branches else None
        ),
        "branch_denominator": branches,
        "missing_branches": info.get("missing_branches", []),
    }


def build_evidence(backend, components, backlog, historical, floor=70):
    backend_files = backend["files"]
    if any(not path.startswith("backend/") or path in MANUAL_SCRIPTS for path in backend_files):
        raise ValueError("Backend denominator contains non-application files")
    selected = {"backend": backend_files}
    for name, path in COMPONENT_PATHS.items():
        selected[name] = {path: components["files"][path]}
    groups = {}
    followups = []
    for name, files in selected.items():
        metrics = {path: file_metric(info) for path, info in files.items()}
        denominator = sum(metric["statement_denominator"] for metric in metrics.values())
        covered = sum(metric["covered_statements"] for metric in metrics.values())
        percent = round(100 * covered / denominator, 1) if denominator else 100.0
        previous_files = historical.get("files", {})
        previous_denominator = (
            sum(previous_files[path]["summary"]["num_statements"] for path in files)
            if all(path in previous_files for path in files) else None
        )
        groups[name] = {
            "statement_percent": percent,
            "baseline_percent": BASELINES[name],
            "delta_percentage_points": round(percent - BASELINES[name], 1),
            "statement_denominator": denominator,
            "historical_statement_denominator": previous_denominator,
            "denominator_delta": (
                denominator - previous_denominator if previous_denominator is not None else None
            ),
            "denominator_note": (
                "Historical artifact lacks the complete backend file set; no like-for-like count claimed."
                if previous_denominator is None else "Statement count compared with tests/sprint4_coverage.json."
            ),
            "files": metrics,
        }
        for path, metric in metrics.items():
            if 100 * metric["covered_statements"] < floor * metric["statement_denominator"]:
                existing = [
                    item["id"] for item in backlog["items"]
                    if item["type"] == "test"
                    and item["status"] not in {"done", "cancelled"}
                    and path in item.get("files", [])
                ]
                followups.append({
                    "file": path, "existing_ids": existing,
                    "proposal": None if existing else {
                        "type": "test", "source": "qa", "priority": "P2",
                        "title": f"Raise coverage for {path}",
                        "description": (
                            f"Run the mocked coverage suite. Expected at least {floor}% statement coverage; "
                            f"actual {metric['statement_percent']}%. Missing lines: {metric['missing_lines']}."
                        ),
                    },
                })
    return {
        "sprint": backlog["current_sprint"], "floor_percent": floor,
        "baseline_source": "agile/reports/sprint-04.md",
        "metric": "statement coverage; branch coverage reported separately, not mixed into deltas",
        "backend_config": "tests/coverage.ini", "excluded_manual_scripts": sorted(MANUAL_SCRIPTS),
        "groups": groups, "followups_for_orchestrator": followups,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", type=Path, default=ROOT / "coverage.json")
    parser.add_argument("--components", type=Path, default=ROOT / "tests/sprint5_component_coverage.json")
    parser.add_argument("--output", type=Path, default=ROOT / "tests/sprint5_coverage_metrics.json")
    parser.add_argument("--junit", type=Path, default=ROOT / ".pytest-report.xml")
    arguments = parser.parse_args(argv)
    evidence = build_evidence(
        json.loads(arguments.backend.read_text()), json.loads(arguments.components.read_text()),
        json.loads((ROOT / "agile/backlog.json").read_text()),
        json.loads((ROOT / "tests/sprint4_coverage.json").read_text()),
    )
    evidence["executed_regressions"] = regression_evidence(arguments.junit)
    arguments.output.write_text(json.dumps(evidence, indent=2) + "\n")
    for name, group in evidence["groups"].items():
        print(f"{name}: {group['statement_percent']}% ({group['delta_percentage_points']:+.1f} pp); "
              f"{group['statement_denominator']} statements; denominator delta={group['denominator_delta']}")
    print(f"Below-floor follow-ups for orchestrator: {len(evidence['followups_for_orchestrator'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())