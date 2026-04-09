"""Unit tests for database repositories."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from Modules.db.database import ConnectionFactory, DatabaseManager, create_schema
from Modules.db.repositories import BasketRepository, ProductRepository
from Modules.models.entities import BasketItem, Product


class TestConnectionFactoryAndSchema(unittest.TestCase):
    def test_create_connection_returns_sqlite_connection(self) -> None:
        connection = ConnectionFactory.create_connection(":memory:")
        try:
            self.assertIsInstance(connection, sqlite3.Connection)
        finally:
            connection.close()

    def test_create_connection_enables_foreign_keys(self) -> None:
        connection = ConnectionFactory.create_connection(":memory:")
        try:
            pragma_value = connection.execute("PRAGMA foreign_keys;").fetchone()
            self.assertEqual(pragma_value[0], 1)
        finally:
            connection.close()

    def test_create_schema_succeeds_and_is_idempotent(self) -> None:
        connection = ConnectionFactory.create_connection(":memory:")
        try:
            create_schema(connection)
            create_schema(connection)
        finally:
            connection.close()

    def test_create_schema_creates_expected_core_tables(self) -> None:
        connection = ConnectionFactory.create_connection(":memory:")
        try:
            create_schema(connection)
            rows = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                ORDER BY name
                """
            ).fetchall()
            table_names = {row[0] for row in rows}
            self.assertTrue(
                {"products", "chains", "stores", "prices", "basket_items"}.issubset(
                    table_names
                )
            )
        finally:
            connection.close()

    def test_create_schema_creates_expected_indexes(self) -> None:
        connection = ConnectionFactory.create_connection(":memory:")
        try:
            create_schema(connection)
            rows = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'index'
                ORDER BY name
                """
            ).fetchall()
            index_names = {row[0] for row in rows}
            expected_indexes = {
                "idx_products_normalized_name",
                "idx_stores_chain_id",
                "idx_prices_product_chain",
                "idx_prices_store_id",
                "idx_basket_items_basket_id",
                "idx_basket_items_product_id",
            }
            self.assertTrue(expected_indexes.issubset(index_names))
        finally:
            connection.close()


class TestDatabaseManager(unittest.TestCase):
    def test_get_connection_uses_configured_database_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "manager.db"
            manager = DatabaseManager(database_path)

            connection = manager.get_connection()
            try:
                self.assertEqual(
                    connection.execute("PRAGMA database_list;").fetchone()[2],
                    str(database_path),
                )
                pragma_value = connection.execute("PRAGMA foreign_keys;").fetchone()
                self.assertEqual(pragma_value[0], 1)
            finally:
                connection.close()

    def test_initialize_database_creates_schema_objects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "init.db"
            manager = DatabaseManager(database_path)

            manager.initialize_database()

            with sqlite3.connect(str(database_path)) as connection:
                rows = connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    ORDER BY name
                    """
                ).fetchall()
                table_names = {row[0] for row in rows}
                self.assertTrue(
                    {"products", "chains", "stores", "prices", "basket_items"}.issubset(
                        table_names
                    )
                )

    def test_initialize_database_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "idempotent.db"
            manager = DatabaseManager(database_path)

            manager.initialize_database()
            manager.initialize_database()

            with sqlite3.connect(str(database_path)) as connection:
                count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM sqlite_master
                    WHERE type = 'table'
                      AND name IN ('products', 'chains', 'stores', 'prices', 'basket_items')
                    """
                ).fetchone()[0]
                self.assertEqual(count, 5)


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


class TestProductRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "products.db"
        self.connection = ConnectionFactory.create_connection(str(self.database_path))
        create_schema(self.connection)
        self.repository = ProductRepository(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.temp_dir.cleanup()

    @staticmethod
    def _make_product(
        *,
        barcode: str,
        name: str,
        normalized_name: str,
        brand: str | None = None,
        unit_name: str | None = None,
    ) -> Product:
        return Product(
            id=None,
            barcode=barcode,
            name=name,
            normalized_name=normalized_name,
            brand=brand,
            unit_name=unit_name,
        )

    def test_upsert_product_inserts_new_product(self) -> None:
        saved = self.repository.upsert_product(
            self._make_product(
                barcode="7290000000001",
                name="Milk 1L",
                normalized_name="milk 1l",
                brand="Dairy Co",
                unit_name="1L",
            )
        )

        self.assertIsNotNone(saved.id)
        self.assertEqual(saved.barcode, "7290000000001")

    def test_upsert_product_updates_existing_row_by_barcode(self) -> None:
        original = self.repository.upsert_product(
            self._make_product(
                barcode="7290000000002",
                name="Bread White",
                normalized_name="bread white",
                brand="Bake Co",
                unit_name="750g",
            )
        )
        updated = self.repository.upsert_product(
            self._make_product(
                barcode="7290000000002",
                name="Bread Whole Wheat",
                normalized_name="bread whole wheat",
                brand="Bake House",
                unit_name="800g",
            )
        )

        self.assertEqual(updated.id, original.id)
        self.assertEqual(updated.name, "Bread Whole Wheat")
        count = self.connection.execute(
            "SELECT COUNT(*) FROM products WHERE barcode = ?",
            ("7290000000002",),
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_get_by_barcode_returns_exact_match(self) -> None:
        self.repository.upsert_product(
            self._make_product(
                barcode="7290000000003",
                name="Eggs L",
                normalized_name="eggs l",
            )
        )

        product = self.repository.get_by_barcode("7290000000003")

        self.assertIsNotNone(product)
        self.assertEqual(product.barcode, "7290000000003")
        self.assertEqual(product.name, "Eggs L")

    def test_get_by_barcode_returns_none_when_missing(self) -> None:
        self.assertIsNone(self.repository.get_by_barcode("0000000000000"))

    def test_get_by_normalized_name_returns_ordered_matches(self) -> None:
        first = self.repository.upsert_product(
            self._make_product(
                barcode="7290000000010",
                name="Tuna in Water",
                normalized_name="tuna",
            )
        )
        second = self.repository.upsert_product(
            self._make_product(
                barcode="7290000000011",
                name="Tuna in Oil",
                normalized_name="tuna",
            )
        )
        self.repository.upsert_product(
            self._make_product(
                barcode="7290000000012",
                name="Corn",
                normalized_name="corn",
            )
        )

        products = self.repository.get_by_normalized_name("tuna")

        self.assertEqual([product.id for product in products], [first.id, second.id])
        self.assertEqual([product.normalized_name for product in products], ["tuna", "tuna"])

    def test_get_by_normalized_name_returns_empty_list_when_missing(self) -> None:
        self.assertEqual(self.repository.get_by_normalized_name("not-found"), [])

    def test_get_by_ids_returns_rows_in_deterministic_order(self) -> None:
        first = self.repository.upsert_product(
            self._make_product(
                barcode="7290000000020",
                name="Cheese",
                normalized_name="cheese",
            )
        )
        second = self.repository.upsert_product(
            self._make_product(
                barcode="7290000000021",
                name="Yogurt",
                normalized_name="yogurt",
            )
        )
        third = self.repository.upsert_product(
            self._make_product(
                barcode="7290000000022",
                name="Butter",
                normalized_name="butter",
            )
        )

        products = self.repository.get_by_ids([third.id, first.id, second.id, 99999])

        self.assertEqual([product.id for product in products], [first.id, second.id, third.id])

    def test_get_by_ids_returns_empty_list_for_empty_input(self) -> None:
        self.assertEqual(self.repository.get_by_ids([]), [])


if __name__ == "__main__":
    unittest.main()
