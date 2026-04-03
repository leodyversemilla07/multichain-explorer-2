"""Tests for architecture boundaries in the active runtime path."""

from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

ACTIVE_RUNTIME_PATHS = [
    REPO_ROOT / "main.py",
    REPO_ROOT / "routers",
    REPO_ROOT / "schemas",
    REPO_ROOT / "services",
]

COMPATIBILITY_ONLY_MODULES = {"compat", "multichain", "performance"}


def _iter_python_files():
    for path in ACTIVE_RUNTIME_PATHS:
        if path.is_file():
            yield path
            continue

        for file_path in sorted(path.rglob("*.py")):
            if "__pycache__" not in file_path.parts:
                yield file_path


def _import_roots(file_path: Path) -> set[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])

    return roots


def test_active_runtime_path_does_not_import_compatibility_only_modules():
    """Active runtime modules should not depend on compatibility-only modules."""
    offenders = []

    for file_path in _iter_python_files():
        imported_roots = _import_roots(file_path)
        forbidden = sorted(imported_roots & COMPATIBILITY_ONLY_MODULES)
        if forbidden:
            offenders.append((file_path.relative_to(REPO_ROOT), forbidden))

    assert offenders == []
