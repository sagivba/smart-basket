"""Unit tests for db repositories."""

from __future__ import annotations

import sqlite3
import unittest

from Modules.db.repositories import ProductRepository
from Modules.models.entities import Product


class TestProductRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute(
            """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                brand TEXT,
                unit_name TEXT
            )
            """
        )
        self.repository = ProductRepository(self.connection)

    def tearDown(self) -> None:
        self.connection.close()

    def test_upsert_product_inserts_new_product(self) -> None:
        product = Product(
            id=None,
            barcode="7290011111111",
            name="Milk 1L",
            normalized_name="milk 1l",
            brand="DairyCo",
            unit_name="1L",
        )

        saved = self.repository.upsert_product(product)

        self.assertIsNotNone(saved.id)
        fetched = self.repository.get_by_barcode("7290011111111")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, saved.id)
        self.assertEqual(fetched.name, "Milk 1L")

    def test_upsert_product_updates_existing_product_by_barcode(self) -> None:
        original = Product(
            id=None,
            barcode="7290011111111",
            name="Milk 1L",
            normalized_name="milk 1l",
            brand="DairyCo",
            unit_name="1L",
        )
        saved = self.repository.upsert_product(original)

        updated = Product(
            id=None,
            barcode="7290011111111",
            name="Milk Updated",
            normalized_name="milk updated",
            brand="NewBrand",
            unit_name="1000ml",
        )
        saved_updated = self.repository.upsert_product(updated)

        self.assertEqual(saved.id, saved_updated.id)
        fetched = self.repository.get_by_barcode("7290011111111")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Milk Updated")
        self.assertEqual(fetched.normalized_name, "milk updated")
        self.assertEqual(fetched.brand, "NewBrand")
        self.assertEqual(fetched.unit_name, "1000ml")

    def test_get_by_barcode_returns_expected_product(self) -> None:
        saved = self.repository.upsert_product(
            Product(
                id=None,
                barcode="7290012222222",
                name="Bread",
                normalized_name="bread",
                brand="BakeCo",
                unit_name="1 unit",
            )
        )

        found = self.repository.get_by_barcode("7290012222222")

        self.assertEqual(found, saved)

    def test_get_by_barcode_returns_none_for_missing_barcode(self) -> None:
        found = self.repository.get_by_barcode("7290099999999")

        self.assertIsNone(found)

    def test_get_by_normalized_name_returns_matching_products(self) -> None:
        first = self.repository.upsert_product(
            Product(
                id=None,
                barcode="7290013000001",
                name="Yogurt Strawberry",
                normalized_name="yogurt",
                brand="DairyCo",
                unit_name="150g",
            )
        )
        second = self.repository.upsert_product(
            Product(
                id=None,
                barcode="7290013000002",
                name="Yogurt Vanilla",
                normalized_name="yogurt",
                brand="DairyCo",
                unit_name="150g",
            )
        )
        self.repository.upsert_product(
            Product(
                id=None,
                barcode="7290013000003",
                name="Cheese",
                normalized_name="cheese",
                brand="DairyCo",
                unit_name="200g",
            )
        )

        found = self.repository.get_by_normalized_name("yogurt")

        self.assertEqual([product.id for product in found], [first.id, second.id])

    def test_get_by_normalized_name_returns_empty_for_missing_name(self) -> None:
        found = self.repository.get_by_normalized_name("non-existent")

        self.assertEqual(found, [])

    def test_get_by_ids_returns_only_requested_products(self) -> None:
        first = self.repository.upsert_product(
            Product(
                id=None,
                barcode="7290014000001",
                name="Rice",
                normalized_name="rice",
                brand="GrainCo",
                unit_name="1kg",
            )
        )
        second = self.repository.upsert_product(
            Product(
                id=None,
                barcode="7290014000002",
                name="Pasta",
                normalized_name="pasta",
                brand="GrainCo",
                unit_name="500g",
            )
        )
        third = self.repository.upsert_product(
            Product(
                id=None,
                barcode="7290014000003",
                name="Beans",
                normalized_name="beans",
                brand="GrainCo",
                unit_name="500g",
            )
        )

        found = self.repository.get_by_ids([third.id, first.id, 9999])

        self.assertEqual([product.id for product in found], [first.id, third.id])
        self.assertNotIn(second.id, [product.id for product in found])


if __name__ == "__main__":
    unittest.main()
