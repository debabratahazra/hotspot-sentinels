#!/usr/bin/env python3
"""Run the test suite with coverage and write the sprint report to agile/reports/."""

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BACKLOG = ROOT / "agile" / "backlog.json"
REPORTS = ROOT / "agile" / "reports"
COVERAGE_JSON = ROOT / "coverage.json"
COVERAGE_CONFIG = ROOT / "tests" / "coverage.ini"


def run_tests() -> dict:
    """Run pytest with coverage. Returns a result dict; never raises on test failure."""
    command = [
        sys.executable, "-m", "pytest", "tests", "-o", "addopts=",
        f"--cov-config={COVERAGE_CONFIG}",
        "--cov=backend", "--cov-report=term-missing", f"--cov-report=json:{COVERAGE_JSON}",
        "-q", "--junit-xml=.pytest-report.xml",
    ]
    printable = shlex.join(command)

    def inconclusive(reason: str) -> dict:
        # Absence of a result is never a pass: callers must rerun before closing anything.
        return {"ran": False, "verdict": "INCONCLUSIVE", "reason": reason, "command": printable}

    if not (ROOT / "tests").is_dir():
        return inconclusive("no tests/ directory yet — QA has not written any tests")

    try:
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        return inconclusive("test run exceeded 15 minutes")

    combined = proc.stdout + proc.stderr
    if "No module named pytest" in combined:
        return inconclusive("pytest is not installed — run: pip install -r requirements.txt")
    if "unrecognized arguments: --cov" in combined:
        return inconclusive("pytest-cov is not installed — run: pip install -r requirements.txt")
    if proc.returncode == 5:
        return inconclusive("pytest collected no tests")

    summary = next((line for line in reversed(proc.stdout.splitlines()) if " passed" in line or " failed" in line
                    or " error" in line), proc.stdout.strip()[-200:] or "no output")
    return {"ran": True, "verdict": "PASS" if proc.returncode == 0 else "FAIL",
            "exit_code": proc.returncode, "summary": summary.strip(),
            "command": printable, "output": proc.stdout}


def test_verdict(tests: dict) -> str:
    """PASS, FAIL or INCONCLUSIVE — a run without a recorded result is never a pass."""
    if tests.get("verdict"):
        return tests["verdict"]
    if not tests.get("ran"):
        return "INCONCLUSIVE"
    return "PASS" if tests.get("exit_code") == 0 else "FAIL"


def read_coverage() -> dict:
    if not COVERAGE_JSON.is_file():
        return {}
    data = json.loads(COVERAGE_JSON.read_text(encoding="utf-8"))
    files = {
        path: round(info["summary"]["percent_covered"], 1)
        for path, info in sorted(data.get("files", {}).items())
    }
    return {"total": round(data["totals"]["percent_covered"], 1), "files": files}


def coverage_lines(coverage: dict) -> list[str]:
    lines = ["", "## Coverage", "",
             f"- Configuration: `{COVERAGE_CONFIG.relative_to(ROOT)}` (backend application code)"]
    if not coverage:
        return lines + ["- No coverage data produced."]
    lines.append(f"- Total: **{coverage['total']}%**")
    lines += ["", "| File | Covered |", "|------|---------|"]
    lines += [f"| {path} | {pct}% |" for path, pct in coverage["files"].items()]
    below = [path for path, pct in coverage["files"].items() if pct < 70]
    if below:
        lines += ["", "Below the 70% floor — needs test tasks next sprint:"]
        lines += [f"- {path}" for path in below]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sprint", nargs="?", type=int)
    parser.add_argument("--no-write", action="store_true", help="Report results to stdout without writing Markdown")
    arguments = parser.parse_args()
    if not BACKLOG.is_file():
        sys.exit(f"No backlog at {BACKLOG}. Run backlog.py init first.")

    data = json.loads(BACKLOG.read_text(encoding="utf-8"))
    sprint_no = arguments.sprint if arguments.sprint is not None else data["current_sprint"]
    sprint = next((s for s in data["sprints"] if s["number"] == sprint_no), None)
    if not sprint:
        sys.exit(f"Sprint {sprint_no} not found.")

    committed = [i for i in data["items"] if i["id"] in sprint.get("committed", [])]
    done = [i for i in committed if i["status"] == "done"]
    # Work pulled into the sprint after planning. Reporting it separately keeps an
    # overrun visible instead of letting it hide inside the committed total.
    unplanned = [i for i in data["items"]
                 if i.get("sprint") == sprint_no and i["id"] not in sprint.get("committed", [])]
    points = lambda items: sum(i.get("estimate") or 0 for i in items)
    open_bugs = [i for i in data["items"] if i["type"] == "bug" and i["status"] not in ("done", "cancelled")]

    tests = run_tests()
    coverage = read_coverage()

    lines = [
        f"# Sprint {sprint_no} Report",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Goal: {sprint.get('goal') or '(none set)'}",
        "",
        "## Delivery",
        "",
        f"- Committed: {len(committed)} item(s), {points(committed)} point(s)",
        f"- Completed: {len(done)}",
        f"- Carried over: {len(committed) - len(done)}",
        f"- Open bugs: {len(open_bugs)}",
    ]
    if unplanned:
        lines += [
            f"- Authorised unplanned: {len(unplanned)} item(s), {points(unplanned)} point(s)",
            f"- **Revised total: {points(committed) + points(unplanned)} point(s)** "
            f"against a {points(committed)}-point commitment",
        ]
    lines += [
        "",
        "| Item | Type | Priority | Status | Scope | Title |",
        "|------|------|----------|--------|-------|-------|",
    ]
    for item in committed:
        lines.append(
            f"| {item['id']} | {item['type']} | {item['priority']} | {item['status']} | committed | {item['title']} |")
    for item in unplanned:
        lines.append(
            f"| {item['id']} | {item['type']} | {item['priority']} | {item['status']} | unplanned | {item['title']} |")

    lines += ["", "## Tests", ""]
    verdict = test_verdict(tests)
    if tests.get("command"):
        lines.append(f"- Command: `{tests['command']}`")
    if tests["ran"]:
        lines += [f"- Result: **{verdict}**", f"- Summary: `{tests['summary']}`"]
    else:
        lines += [f"- Result: **{verdict}**", f"- Reason: {tests['reason']}",
                  "- This run produced no authoritative result and is not a pass. Rerun to completion before closing any item."]

    lines += coverage_lines(coverage)

    if open_bugs:
        lines += ["", "## Open bugs carried forward", ""]
        lines += [f"- {b['id']} ({b['priority']}) {b['title']}" for b in open_bugs]

    if not arguments.no_write:
        REPORTS.mkdir(parents=True, exist_ok=True)
        path = REPORTS / f"sprint-{sprint_no:02d}.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")
    print(f"Coverage configuration: {COVERAGE_CONFIG.relative_to(ROOT)} (backend application code)")
    if tests["ran"]:
        print(tests["summary"])
    for path, pct in coverage.get("files", {}).items():
        print(f"{path}: {pct}%")
    print(f"tests={test_verdict(tests)} "
          f"coverage={coverage.get('total', 'n/a')} done={len(done)}/{len(committed)} open_bugs={len(open_bugs)}")
    return tests.get("exit_code", 1)


if __name__ == "__main__":
    raise SystemExit(main())
