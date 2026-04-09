"""Integration evidence that bootstrap/run flows execute without network access."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Modules.app.cli import run_cli


class TestOfflineBootstrapIntegration(unittest.TestCase):
    """Verifies a local bootstrap/load/run flow with network calls blocked."""

    def test_cli_bootstrap_load_and_compare_run_with_network_blocked(self) -> None:
        fixtures_dir = Path("tests/fixtures")

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "offline.sqlite"

            with patch("socket.create_connection", side_effect=AssertionError("network disabled in test")), patch(
                "socket.socket.connect", side_effect=AssertionError("network disabled in test")
            ):
                stores_exit, stores_stdout, stores_stderr = self._run_cli(
                    [
                        "--db-path",
                        str(db_path),
                        "load",
                        "stores",
                        str(fixtures_dir / "import_stores.csv"),
                        "--mode",
                        "replace",
                    ]
                )
                products_exit, products_stdout, products_stderr = self._run_cli(
                    [
                        "--db-path",
                        str(db_path),
                        "load",
                        "products",
                        str(fixtures_dir / "import_products.csv"),
                        "--mode",
                        "replace",
                    ]
                )
                prices_exit, prices_stdout, prices_stderr = self._run_cli(
                    [
                        "--db-path",
                        str(db_path),
                        "load",
                        "prices",
                        str(fixtures_dir / "import_prices.csv"),
                        "--mode",
                        "append",
                    ]
                )
                add_matched_exit, add_matched_stdout, add_matched_stderr = self._run_cli(
                    [
                        "--db-path",
                        str(db_path),
                        "add-item",
                        "1",
                        "12345678",
                        "--input-type",
                        "barcode",
                        "--quantity",
                        "2",
                    ]
                )
                add_unmatched_exit, add_unmatched_stdout, add_unmatched_stderr = self._run_cli(
                    [
                        "--db-path",
                        str(db_path),
                        "add-item",
                        "1",
                        "not-in-catalog",
                        "--input-type",
                        "name",
                        "--quantity",
                        "1",
                    ]
                )
                compare_exit, compare_stdout, compare_stderr = self._run_cli(
                    [
                        "--db-path",
                        str(db_path),
                        "compare",
                        "1",
                    ]
                )

        self.assertEqual(stores_exit, 0)
        self.assertEqual(products_exit, 0)
        self.assertEqual(prices_exit, 0)
        self.assertEqual(add_matched_exit, 0)
        self.assertEqual(add_unmatched_exit, 0)
        self.assertEqual(compare_exit, 0)

        self.assertEqual(stores_stderr, "")
        self.assertEqual(products_stderr, "")
        self.assertEqual(prices_stderr, "")
        self.assertEqual(add_matched_stderr, "")
        self.assertEqual(add_unmatched_stderr, "")
        self.assertEqual(compare_stderr, "")

        self.assertIn("Loaded stores: accepted=6, rejected=0", stores_stdout)
        self.assertIn("Loaded products: accepted=4, rejected=0", products_stdout)
        self.assertIn("Loaded prices: accepted=4, rejected=0", prices_stdout)
        self.assertIn("status=matched", add_matched_stdout)
        self.assertIn("status=unmatched", add_unmatched_stdout)
        self.assertIn("Ranked chain comparison:", compare_stdout)
        self.assertIn("1. Chain A", compare_stdout)
        self.assertIn("Unmatched items: not-in-catalog", compare_stdout)

    def _run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_cli(argv, stdout=stdout, stderr=stderr)
        return exit_code, stdout.getvalue(), stderr.getvalue()


if __name__ == "__main__":
    unittest.main()
