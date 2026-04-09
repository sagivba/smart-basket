"""Integration tests for end-to-end import flow."""

from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from Modules.data.data_loader import PriceDataLoader
from Modules.db.database import create_schema


class TestImportFlow(unittest.TestCase):
    """Validate deterministic parser-to-loader database import flow."""

    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        create_schema(self.connection)
        self.loader = PriceDataLoader(self.connection)
        self.fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"

    def tearDown(self) -> None:
        self.connection.close()

    def test_import_products_and_stores_and_prices_persists_expected_rows(self) -> None:
        stores_result = self.loader.load_stores(
            self.fixtures_dir / "import_stores.csv",
            mode="replace",
        )

        products_result = self.loader.load_products(
            self.fixtures_dir / "import_products.csv",
            mode="replace",
        )
        prices_result = self.loader.load_prices(
            self.fixtures_dir / "import_prices.csv",
            mode="append",
        )

        self.assertTrue(stores_result.success)
        self.assertEqual(stores_result.accepted_count, 6)
        self.assertEqual(stores_result.rejected_count, 0)

        chain_rows = self.connection.execute(
            "SELECT chain_code, name FROM chains ORDER BY chain_code"
        ).fetchall()
        self.assertEqual(
            chain_rows,
            [("CHAIN_A", "Chain A"), ("CHAIN_B", "Chain B")],
        )

        store_rows = self.connection.execute(
            """
            SELECT c.chain_code, s.store_code, s.name, s.city, s.address, s.is_active
            FROM stores s
            JOIN chains c ON c.id = s.chain_id
            ORDER BY c.chain_code, s.store_code
            """
        ).fetchall()
        self.assertEqual(
            store_rows,
            [
                ("CHAIN_A", "STORE_1", "Chain A Downtown", "Tel Aviv", "Main 1", 1),
                ("CHAIN_A", "STORE_2", "Chain A North", "Haifa", "Harbor 10", 1),
                ("CHAIN_B", "STORE_9", "Chain B Center", "Jerusalem", "Market 5", 0),
            ],
        )

        self.assertTrue(products_result.success)
        self.assertEqual(products_result.accepted_count, 4)
        self.assertEqual(products_result.rejected_count, 0)

        self.assertTrue(prices_result.success)
        self.assertEqual(prices_result.accepted_count, 4)
        self.assertEqual(prices_result.rejected_count, 0)

        product_rows = self.connection.execute(
            "SELECT barcode, name, normalized_name, brand, unit_name FROM products ORDER BY barcode"
        ).fetchall()
        self.assertEqual(
            product_rows,
            [
                ("12345678", "Milk 1L", "milk 1l", "DairyCo", "1L"),
                ("87654321", "Bread Whole", "bread whole", "BakeCo", "700g"),
            ],
        )

        price_rows = self.connection.execute(
            """
            SELECT p.barcode, c.chain_code, s.store_code, pr.price, pr.currency, pr.price_date
            FROM prices pr
            JOIN products p ON p.id = pr.product_id
            JOIN chains c ON c.id = pr.chain_id
            JOIN stores s ON s.id = pr.store_id
            ORDER BY p.barcode
            """
        ).fetchall()
        self.assertEqual(
            price_rows,
            [
                ("12345678", "CHAIN_A", "STORE_1", 5.9, "ILS", "2026-01-15"),
                ("87654321", "CHAIN_A", "STORE_1", 7.5, "ILS", "2026-01-15"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
