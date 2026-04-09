"""Unit tests for database repositories."""

from __future__ import annotations

import sqlite3
import unittest

from Modules.db.repositories import BasketRepository
from Modules.models.entities import BasketItem


class TestBasketRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute(
            """
            CREATE TABLE basket_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                basket_id INTEGER NOT NULL,
                product_id INTEGER NULL,
                input_value TEXT NOT NULL,
                input_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                match_status TEXT NOT NULL
            )
            """
        )
        self.repository = BasketRepository(self.connection)

    def tearDown(self) -> None:
        self.connection.close()

    def _make_item(
        self,
        *,
        basket_id: int,
        product_id: int | None,
        input_value: str,
        input_type: str,
        quantity: int,
        match_status: str,
    ) -> BasketItem:
        return BasketItem(
            id=None,
            basket_id=basket_id,
            product_id=product_id,
            input_value=input_value,
            input_type=input_type,
            quantity=quantity,
            match_status=match_status,
        )

    def test_add_item_persists_basket_item(self) -> None:
        item = self._make_item(
            basket_id=100,
            product_id=11,
            input_value="7290011111111",
            input_type="barcode",
            quantity=2,
            match_status="matched",
        )

        saved = self.repository.add_item(item)

        self.assertIsNotNone(saved.id)
        self.assertEqual(saved.basket_id, 100)
        self.assertEqual(saved.product_id, 11)

        persisted_rows = self.connection.execute(
            "SELECT COUNT(*) FROM basket_items WHERE basket_id = ?", (100,)
        ).fetchone()
        self.assertEqual(persisted_rows[0], 1)

    def test_get_by_basket_id_returns_only_requested_basket_items(self) -> None:
        self.repository.add_item(
            self._make_item(
                basket_id=200,
                product_id=11,
                input_value="milk",
                input_type="name",
                quantity=1,
                match_status="matched",
            )
        )
        self.repository.add_item(
            self._make_item(
                basket_id=200,
                product_id=12,
                input_value="bread",
                input_type="name",
                quantity=2,
                match_status="matched",
            )
        )
        self.repository.add_item(
            self._make_item(
                basket_id=201,
                product_id=13,
                input_value="eggs",
                input_type="name",
                quantity=1,
                match_status="matched",
            )
        )

        basket_items = self.repository.get_by_basket_id(200)

        self.assertEqual(len(basket_items), 2)
        self.assertTrue(all(item.basket_id == 200 for item in basket_items))
        self.assertEqual([item.input_value for item in basket_items], ["milk", "bread"])

    def test_get_by_basket_id_returns_empty_list_for_missing_basket(self) -> None:
        basket_items = self.repository.get_by_basket_id(999)

        self.assertEqual(basket_items, [])

    def test_update_item_updates_existing_row_fields(self) -> None:
        created = self.repository.add_item(
            self._make_item(
                basket_id=300,
                product_id=21,
                input_value="old milk",
                input_type="name",
                quantity=1,
                match_status="unmatched",
            )
        )

        updated = BasketItem(
            id=created.id,
            basket_id=301,
            product_id=22,
            input_value="new milk",
            input_type="barcode",
            quantity=3,
            match_status="matched",
        )

        self.repository.update_item(updated)

        row = self.connection.execute(
            """
            SELECT basket_id, product_id, input_value, input_type, quantity, match_status
            FROM basket_items
            WHERE id = ?
            """,
            (created.id,),
        ).fetchone()

        self.assertEqual(row, (301, 22, "new milk", "barcode", 3, "matched"))

    def test_delete_item_removes_only_targeted_row(self) -> None:
        first = self.repository.add_item(
            self._make_item(
                basket_id=400,
                product_id=31,
                input_value="item-a",
                input_type="name",
                quantity=1,
                match_status="matched",
            )
        )
        second = self.repository.add_item(
            self._make_item(
                basket_id=400,
                product_id=32,
                input_value="item-b",
                input_type="name",
                quantity=1,
                match_status="matched",
            )
        )

        self.repository.delete_item(first.id)

        rows = self.connection.execute(
            "SELECT id, input_value FROM basket_items ORDER BY id"
        ).fetchall()
        self.assertEqual(rows, [(second.id, "item-b")])

    def test_delete_one_item_does_not_affect_other_baskets(self) -> None:
        first = self.repository.add_item(
            self._make_item(
                basket_id=500,
                product_id=41,
                input_value="basket-500-item",
                input_type="name",
                quantity=1,
                match_status="matched",
            )
        )
        second = self.repository.add_item(
            self._make_item(
                basket_id=501,
                product_id=42,
                input_value="basket-501-item",
                input_type="name",
                quantity=1,
                match_status="matched",
            )
        )

        self.repository.delete_item(first.id)

        basket_500_items = self.repository.get_by_basket_id(500)
        basket_501_items = self.repository.get_by_basket_id(501)

        self.assertEqual(basket_500_items, [])
        self.assertEqual(len(basket_501_items), 1)
        self.assertEqual(basket_501_items[0].id, second.id)


if __name__ == "__main__":
    unittest.main()
