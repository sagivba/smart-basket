"""Integration validation for comparison behavior with imported real retailer fixtures."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from Modules.app.application_service import CompareBasketUseCase
from Modules.app.cli import CliMatcher, SqliteBasketComparisonService
from Modules.data.data_loader import PriceDataLoader
from Modules.data.downloaded_import import DownloadedImportOrchestrator
from Modules.db.database import create_schema
from Modules.db.repositories import BasketRepository


class TestRealDataComparisonValidation(unittest.TestCase):
    """Validate ranking and match-status behavior after importing retailer fixtures."""

    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        create_schema(self.connection)
        self.loader = PriceDataLoader(self.connection)
        self.orchestrator = DownloadedImportOrchestrator(loader=self.loader)
        self.matcher = CliMatcher(self.connection)
        self.basket_repository = BasketRepository(self.connection)
        self.compare_use_case = CompareBasketUseCase(
            basket_repository=self.basket_repository,
            comparison_service=SqliteBasketComparisonService(self.connection),
        )
        self.fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "integration"

    def tearDown(self) -> None:
        self.connection.close()

    def test_compare_basket_uses_imported_prices_and_keeps_partial_unmatched_ambiguous_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            download_root = Path(temp_dir) / "downloads"
            chain_dir = download_root / "real_retailers"
            chain_dir.mkdir(parents=True, exist_ok=True)

            shutil.copy(
                self.fixtures_dir / "real_import_stores.csv",
                chain_dir / "Stores_20260201.csv",
            )
            shutil.copy(
                self.fixtures_dir / "real_import_products.csv",
                chain_dir / "Products_20260201.csv",
            )
            shutil.copy(
                self.fixtures_dir / "real_import_prices.csv",
                chain_dir / "PriceFull_20260201.csv",
            )

            summary = self.orchestrator.import_downloaded_tree(download_root, mode="append")

        self.assertTrue(summary.success)
        self.assertEqual(summary.discovered_count, 3)
        self.assertEqual(summary.success_count, 3)
        self.assertEqual(summary.rejected_rows, 0)
        imported_counts = self.connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM stores),
                (SELECT COUNT(*) FROM products),
                (SELECT COUNT(*) FROM prices)
            """
        ).fetchone()
        self.assertEqual(imported_counts, (4, 4, 10))

        basket_id = 77
        persisted_items = [
            self.basket_repository.add_item(
                self.matcher.to_basket_item(
                    basket_id=basket_id,
                    input_type="barcode",
                    input_value="7290000000011",
                    quantity=1,
                )
            ),
            self.basket_repository.add_item(
                self.matcher.to_basket_item(
                    basket_id=basket_id,
                    input_type="name",
                    input_value="Bread Whole",
                    quantity=1,
                )
            ),
            self.basket_repository.add_item(
                self.matcher.to_basket_item(
                    basket_id=basket_id,
                    input_type="name",
                    input_value="Tomato Sauce",
                    quantity=1,
                )
            ),
            self.basket_repository.add_item(
                self.matcher.to_basket_item(
                    basket_id=basket_id,
                    input_type="name",
                    input_value="Dragon Fruit",
                    quantity=1,
                )
            ),
        ]

        self.assertEqual([item.match_status for item in persisted_items], ["matched", "matched", "ambiguous", "unmatched"])

        result = self.compare_use_case.execute(basket_id=basket_id)

        self.assertEqual(result.unmatched_items, ["tomato sauce", "dragon fruit"])
        self.assertEqual(len(result.ranked_chains), 2)

        complete_chain = result.ranked_chains[0]
        partial_chain = result.ranked_chains[1]

        self.assertEqual(complete_chain.chain_name, "Rami Value")
        self.assertTrue(complete_chain.is_complete_basket)
        self.assertEqual(complete_chain.total_price, 14.2)
        self.assertEqual([line.unit_price for line in complete_chain.basket_lines], [6.0, 8.2])

        self.assertEqual(partial_chain.chain_name, "Shuf Market")
        self.assertFalse(partial_chain.is_complete_basket)
        self.assertEqual(partial_chain.total_price, 5.0)
        self.assertEqual(partial_chain.missing_items, ["Bread Whole"])


if __name__ == "__main__":
    unittest.main()
