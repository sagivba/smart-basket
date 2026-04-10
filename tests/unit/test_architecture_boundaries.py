"""Architecture guardrails for layer-boundary verification."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


class TestArchitectureBoundaries(unittest.TestCase):
    """Verifies key layer boundaries stay aligned with MVP architecture."""

    def _module_files(self, module_name: str) -> list[Path]:
        module_root = REPO_ROOT / "Modules" / module_name
        return sorted(path for path in module_root.rglob("*.py") if path.is_file())

    def _parse_file(self, file_path: Path) -> ast.AST:
        return ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))

    def _collect_import_roots(self, tree: ast.AST) -> set[str]:
        roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    roots.add(alias.name.split(".", 1)[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".", 1)[0])
        return roots

    def _collect_full_imports(self, tree: ast.AST) -> set[str]:
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        return imports

    def test_app_use_case_module_stays_thin_and_layer_oriented(self) -> None:
        file_path = REPO_ROOT / "Modules" / "app" / "application_service.py"
        tree = self._parse_file(file_path)
        full_imports = self._collect_full_imports(tree)

        forbidden_prefixes = (
            "Modules.engine",
            "Modules.data",
            "Modules.db",
        )
        violations = [
            imported
            for imported in sorted(full_imports)
            if imported.startswith(forbidden_prefixes)
        ]

        self.assertEqual(
            [],
            violations,
            msg=(
                "Application service use cases should remain thin orchestration and avoid "
                "depending on concrete engine/data/db modules:\n" + "\n".join(violations)
            ),
        )

    def test_engine_module_does_not_use_file_io_or_parser_dependencies(self) -> None:
        violations: list[str] = []
        forbidden_import_roots = {"csv", "json", "pathlib", "sqlite3"}

        for file_path in self._module_files("engine"):
            tree = self._parse_file(file_path)
            import_roots = self._collect_import_roots(tree)
            full_imports = self._collect_full_imports(tree)

            for module_root in sorted(import_roots & forbidden_import_roots):
                violations.append(f"{file_path.relative_to(REPO_ROOT)} imports {module_root}")

            for imported in sorted(full_imports):
                if imported.startswith("Modules.data"):
                    violations.append(
                        f"{file_path.relative_to(REPO_ROOT)} imports forbidden module {imported}"
                    )

            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
                    violations.append(
                        f"{file_path.relative_to(REPO_ROOT)} calls open() directly"
                    )

        self.assertEqual(
            [],
            violations,
            msg=(
                "Engine layer should not perform file IO or parsing-module access:\n"
                + "\n".join(violations)
            ),
        )

    def test_data_module_does_not_depend_on_engine_or_comparison_apis(self) -> None:
        violations: list[str] = []

        for file_path in self._module_files("data"):
            tree = self._parse_file(file_path)
            full_imports = self._collect_full_imports(tree)

            for imported in sorted(full_imports):
                if imported.startswith("Modules.engine"):
                    violations.append(
                        f"{file_path.relative_to(REPO_ROOT)} imports forbidden module {imported}"
                    )

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name in {"compare_basket", "rank_chains"}:
                    violations.append(
                        f"{file_path.relative_to(REPO_ROOT)} defines comparison function {node.name}"
                    )

        self.assertEqual(
            [],
            violations,
            msg=(
                "Data layer should not implement basket comparison/ranking responsibilities:\n"
                + "\n".join(violations)
            ),
        )

    def test_db_module_does_not_depend_on_engine_or_data_parsers(self) -> None:
        violations: list[str] = []

        for file_path in self._module_files("db"):
            tree = self._parse_file(file_path)
            full_imports = self._collect_full_imports(tree)

            for imported in sorted(full_imports):
                if imported.startswith("Modules.engine") or imported.startswith("Modules.data"):
                    violations.append(
                        f"{file_path.relative_to(REPO_ROOT)} imports forbidden module {imported}"
                    )

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("rank"):
                    violations.append(
                        f"{file_path.relative_to(REPO_ROOT)} defines ranking function {node.name}"
                    )

        self.assertEqual(
            [],
            violations,
            msg=(
                "DB layer should stay persistence-focused and avoid business ranking concerns:\n"
                + "\n".join(violations)
            ),
        )


if __name__ == "__main__":
    unittest.main()
