"""Integration tests for downloaded-tree discovery to parse/load orchestration."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from Modules.data.data_loader import PriceDataLoader
from Modules.data.downloaded_import import DownloadedImportOrchestrator
from Modules.db.database import create_schema


class TestDownloadedImportFlow(unittest.TestCase):
    """Validate downloaded file discovery through parser and loader integration."""

    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        create_schema(self.connection)
        self.loader = PriceDataLoader(self.connection)
        self.orchestrator = DownloadedImportOrchestrator(loader=self.loader)
        self.fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"

    def tearDown(self) -> None:
        self.connection.close()

    def test_import_downloaded_tree_processes_files_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            download_root = Path(temp_dir) / "downloads"
            chain_dir = download_root / "shufersal" / "Shufersal"
            chain_dir.mkdir(parents=True, exist_ok=True)

            shutil.copy(self.fixtures_dir / "import_stores.csv", chain_dir / "Stores_20260115.csv")
            shutil.copy(self.fixtures_dir / "import_products.csv", chain_dir / "Products_20260115.csv")
            shutil.copy(self.fixtures_dir / "import_prices.csv", chain_dir / "PriceFull_20260115.csv")

            summary = self.orchestrator.import_downloaded_tree(download_root, mode="append")

        self.assertTrue(summary.success)
        self.assertEqual(summary.discovered_count, 3)
        self.assertEqual(summary.imported_count, 3)
        self.assertEqual(summary.success_count, 3)
        self.assertEqual(summary.failed_count, 0)
        self.assertEqual(summary.accepted_rows, 14)
        self.assertEqual(summary.rejected_rows, 0)

        chain_rows = self.connection.execute("SELECT chain_code, name FROM chains ORDER BY chain_code").fetchall()
        self.assertEqual(chain_rows, [("CHAIN_A", "Chain A"), ("CHAIN_B", "Chain B")])

        counts = self.connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM stores),
                (SELECT COUNT(*) FROM products),
                (SELECT COUNT(*) FROM prices)
            """
        ).fetchone()
        self.assertEqual(counts, (3, 2, 2))

    def test_import_downloaded_tree_collects_discovery_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            download_root = Path(temp_dir) / "downloads"
            chain_dir = download_root / "hazi_hinam"
            chain_dir.mkdir(parents=True, exist_ok=True)

            shutil.copy(self.fixtures_dir / "import_stores.csv", chain_dir / "Stores_20260115.csv")
            (chain_dir / "README.txt").write_text("ignored", encoding="utf-8")
            (chain_dir / "UnknownFeed.csv").write_text("a,b\n1,2\n", encoding="utf-8")

            summary = self.orchestrator.import_downloaded_tree(download_root, mode="append")

        self.assertTrue(summary.success)
        self.assertEqual(summary.discovered_count, 1)
        self.assertEqual(summary.imported_count, 1)
        self.assertEqual(summary.accepted_rows, 6)
        self.assertEqual(summary.rejected_rows, 0)
        self.assertEqual(len(summary.warnings), 2)
        self.assertTrue(any("unsupported file extension" in warning for warning in summary.warnings))
        self.assertTrue(any("unrecognized retailer file" in warning for warning in summary.warnings))


if __name__ == "__main__":
    unittest.main()
