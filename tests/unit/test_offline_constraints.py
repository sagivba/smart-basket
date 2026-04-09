"""Offline-execution guardrails for the current MVP repository."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_NETWORK_MODULES = {
    "aiohttp",
    "boto3",
    "botocore",
    "ftplib",
    "grpc",
    "http",
    "httpx",
    "paramiko",
    "requests",
    "smtplib",
    "socket",
    "urllib",
    "urllib3",
    "websocket",
    "websockets",
}


class TestOfflineExecutionConstraints(unittest.TestCase):
    """Verifies that current runtime/test code stays local-only."""

    def _iter_python_files(self, relative_root: str) -> list[Path]:
        root = REPO_ROOT / relative_root
        return sorted(path for path in root.rglob("*.py") if path.is_file())

    def _collect_forbidden_imports(self, files: list[Path]) -> list[str]:
        violations: list[str] = []
        for file_path in files:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_root = alias.name.split(".", 1)[0]
                        if module_root in FORBIDDEN_NETWORK_MODULES:
                            violations.append(f"{file_path.relative_to(REPO_ROOT)}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module_root = node.module.split(".", 1)[0]
                    if module_root in FORBIDDEN_NETWORK_MODULES:
                        violations.append(
                            f"{file_path.relative_to(REPO_ROOT)}: from {node.module} import ..."
                        )
        return violations

    def test_modules_and_tests_do_not_import_network_clients(self) -> None:
        files = self._iter_python_files("Modules") + self._iter_python_files("tests")
        violations = self._collect_forbidden_imports(files)

        self.assertEqual(
            [],
            violations,
            msg=(
                "Found network-related imports that violate local/offline MVP constraints:\n"
                + "\n".join(violations)
            ),
        )

    def test_requirements_file_has_expected_runtime_dependencies(self) -> None:
        requirements_lines = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        pinned_dependencies = [
            line.strip()
            for line in requirements_lines
            if line.strip() and not line.strip().startswith("#")
        ]

        self.assertEqual(
            ["il-supermarket-scraper==1.0.0"],
            pinned_dependencies,
            msg=(
                "requirements.txt should keep a minimal explicit dependency set for MVP. "
                "Unexpected dependency changes require review."
            ),
        )


if __name__ == "__main__":
    unittest.main()
