"""US-01.5 — the backend packages must import identically from pytest and from uvicorn."""

import ast
import importlib
from io import StringIO
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / "backend"

PATH_MUTATORS = {("sys", "path", "append"), ("sys", "path", "insert")}


def _imported_modules(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            yield node.lineno, base
            for alias in node.names:
                yield node.lineno, f"{base}.{alias.name}"


def test_services_package_importable(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "offline-import-test")
    with patch("os.popen", return_value=StringIO("")), patch(
        "google.genai.Client", side_effect=AssertionError("Import constructed a cloud client")
    ):
        module = importlib.import_module("services.vision_analyzer")
    assert Path(module.__file__).resolve() == BACKEND / "services" / "vision_analyzer.py"


def test_tools_package_importable():
    module = importlib.import_module("tools")
    assert Path(module.__file__).resolve() == BACKEND / "tools" / "__init__.py"


def test_backend_imports_do_not_mutate_interpreter_search_directories():
    for source in BACKEND.rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            target = node.func.value
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                call = (target.value.id, target.attr, node.func.attr)
                assert call not in PATH_MUTATORS, f"path mutation in {source}:{node.lineno}"


def test_service_layer_does_not_import_main():
    for package, sibling in (("services", "tools"), ("tools", "services")):
        for source in (BACKEND / package).rglob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for lineno, module in _imported_modules(tree):
                forbidden = {"main", sibling}.intersection(module.split("."))
                assert not forbidden, f"layering violation in {source}:{lineno}: {module}"