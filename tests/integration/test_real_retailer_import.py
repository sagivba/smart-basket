"""Integration tests for real retailer-file import flow into SQLite."""

from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from Modules.data.data_loader import PriceDataLoader
from Modules.db.database import create_schema


class TestRealRetailerImportFlow(unittest.TestCase):
    """Validate end-to-end persistence for representative retailer fixtures."""

    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        create_schema(self.connection)
        self.loader = PriceDataLoader(self.connection)
        self.fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "retailer"

    def tearDown(self) -> None:
        self.connection.close()

    def test_real_retailer_import_is_idempotent_for_repeated_append_batches(self) -> None:
        stores_result = self.loader.load_stores(self.fixtures_dir / "stores_real.csv", mode="replace")
        products_result = self.loader.load_products(self.fixtures_dir / "products_real.csv", mode="replace")

        first_prices = self.loader.load_prices(self.fixtures_dir / "prices_real_batch_1.csv", mode="append")
        repeated_prices = self.loader.load_prices(self.fixtures_dir / "prices_real_batch_1.csv", mode="append")

        self.assertTrue(stores_result.success)
        self.assertTrue(products_result.success)
        self.assertTrue(first_prices.success)
        self.assertTrue(repeated_prices.success)

        chain_rows = self.connection.execute(
            "SELECT chain_code, name FROM chains ORDER BY chain_code"
        ).fetchall()
        self.assertEqual(
            chain_rows,
            [("7290058", "Shufersal"), ("7290873", "Hazi Hinam")],
        )

        prices_count = self.connection.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
        self.assertEqual(prices_count, 2)

    def test_real_retailer_replace_mode_replaces_previous_price_batch(self) -> None:
        self.loader.load_stores(self.fixtures_dir / "stores_real.csv", mode="replace")
        self.loader.load_products(self.fixtures_dir / "products_real.csv", mode="replace")

        append_result = self.loader.load_prices(self.fixtures_dir / "prices_real_batch_1.csv", mode="append")
        replace_result = self.loader.load_prices(self.fixtures_dir / "prices_real_batch_2.csv", mode="replace")

        self.assertTrue(append_result.success)
        self.assertTrue(replace_result.success)

        price_rows = self.connection.execute(
            """
            SELECT c.chain_code, s.store_code, p.barcode, CAST(pr.price AS REAL), pr.currency, pr.price_date
            FROM prices pr
            JOIN chains c ON c.id = pr.chain_id
            JOIN stores s ON s.id = pr.store_id
            JOIN products p ON p.id = pr.product_id
            ORDER BY s.store_code, p.barcode
            """
        ).fetchall()
        self.assertEqual(
            price_rows,
            [
                ("7290058", "001", "7290001111111", 6.4, "ILS", "2026-02-01"),
                ("7290058", "002", "7290001111111", 6.2, "ILS", "2026-02-01"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
