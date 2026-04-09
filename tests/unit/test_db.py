"""Unit tests for database repositories."""

from __future__ import annotations

import sqlite3
import unittest
from datetime import date
from decimal import Decimal

from Modules.db.repositories import PriceRepository
from Modules.models.entities import Price


class PriceRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute(
            """
            CREATE TABLE prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                chain_id INTEGER NOT NULL,
                store_id INTEGER NOT NULL,
                price TEXT NOT NULL,
                currency TEXT NOT NULL,
                price_date TEXT NOT NULL,
                source_file TEXT
            )
            """
        )
        self.repository = PriceRepository(self.connection)

    def tearDown(self) -> None:
        self.connection.close()

    def test_upsert_price_inserts_new_row(self) -> None:
        price = Price(
            id=None,
            product_id=1,
            chain_id=10,
            store_id=100,
            price=Decimal("9.99"),
            currency="ILS",
            price_date=date(2026, 4, 9),
            source_file="prices_a.csv",
        )

        saved = self.repository.upsert_price(price)

        self.assertIsNotNone(saved.id)
        self.assertEqual(saved.price, Decimal("9.99"))

        count = self.connection.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
        self.assertEqual(count, 1)

    def test_upsert_price_updates_existing_row_by_uniqueness_keys(self) -> None:
        self.repository.upsert_price(
            Price(
                id=None,
                product_id=1,
                chain_id=10,
                store_id=100,
                price=Decimal("9.99"),
                currency="ILS",
                price_date=date(2026, 4, 9),
                source_file="prices_a.csv",
            )
        )

        updated = self.repository.upsert_price(
            Price(
                id=None,
                product_id=1,
                chain_id=10,
                store_id=100,
                price=Decimal("8.49"),
                currency="ILS",
                price_date=date(2026, 4, 9),
                source_file="prices_b.csv",
            )
        )

        self.assertEqual(updated.price, Decimal("8.49"))

        rows = self.connection.execute(
            "SELECT price, source_file FROM prices WHERE product_id = 1 AND chain_id = 10 AND store_id = 100"
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "8.49")
        self.assertEqual(rows[0][1], "prices_b.csv")

    def test_get_by_product_and_chain_returns_representative_min_price(self) -> None:
        self.repository.upsert_price(
            Price(None, 1, 10, 100, Decimal("12.00"), "ILS", date(2026, 4, 9), None)
        )
        self.repository.upsert_price(
            Price(None, 1, 10, 200, Decimal("10.50"), "ILS", date(2026, 4, 9), None)
        )

        selected = self.repository.get_by_product_and_chain(product_id=1, chain_id=10)

        self.assertIsNotNone(selected)
        self.assertEqual(selected.price, Decimal("10.50"))
        self.assertEqual(selected.store_id, 200)

    def test_get_by_product_and_chain_missing_returns_none(self) -> None:
        selected = self.repository.get_by_product_and_chain(product_id=999, chain_id=10)
        self.assertIsNone(selected)

    def test_get_prices_for_products_by_chain_returns_only_requested_ids(self) -> None:
        self.repository.upsert_price(
            Price(None, 1, 10, 100, Decimal("4.00"), "ILS", date(2026, 4, 9), None)
        )
        self.repository.upsert_price(
            Price(None, 2, 10, 100, Decimal("7.00"), "ILS", date(2026, 4, 9), None)
        )
        self.repository.upsert_price(
            Price(None, 3, 10, 100, Decimal("3.00"), "ILS", date(2026, 4, 9), None)
        )

        results = self.repository.get_prices_for_products_by_chain([1, 2], chain_id=10)

        self.assertEqual(set(results.keys()), {1, 2})
        self.assertNotIn(3, results)

    def test_get_prices_for_products_by_chain_uses_chain_min_price_and_no_chain_leak(self) -> None:
        self.repository.upsert_price(
            Price(None, 1, 10, 100, Decimal("9.50"), "ILS", date(2026, 4, 9), None)
        )
        self.repository.upsert_price(
            Price(None, 1, 10, 101, Decimal("8.00"), "ILS", date(2026, 4, 9), None)
        )
        self.repository.upsert_price(
            Price(None, 1, 20, 500, Decimal("1.00"), "ILS", date(2026, 4, 9), None)
        )

        results = self.repository.get_prices_for_products_by_chain([1], chain_id=10)

        self.assertIn(1, results)
        self.assertEqual(results[1].chain_id, 10)
        self.assertEqual(results[1].price, Decimal("8.00"))
        self.assertNotEqual(results[1].price, Decimal("1.00"))


if __name__ == "__main__":
    unittest.main()
