"""Unit tests for database repositories."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from Modules.db.database import ConnectionFactory, DatabaseManager, create_schema
from Modules.db.repositories import BasketRepository, ChainRepository, StoreRepository
from Modules.models.entities import BasketItem, Chain, Store


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


class TestChainRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = ConnectionFactory.create_connection(":memory:")
        create_schema(self.connection)
        self.repository = ChainRepository(self.connection)

    def tearDown(self) -> None:
        self.connection.close()

    def test_upsert_inserts_new_chain(self) -> None:
        persisted = self.repository.upsert(Chain(id=None, chain_code="729005", name="Fresh Mart"))

        self.assertIsNotNone(persisted.id)
        self.assertEqual(persisted.chain_code, "729005")
        self.assertEqual(persisted.name, "Fresh Mart")

    def test_upsert_updates_existing_chain_by_chain_code(self) -> None:
        first = self.repository.upsert(Chain(id=None, chain_code="729006", name="Initial Name"))

        second = self.repository.upsert(Chain(id=None, chain_code="729006", name="Updated Name"))

        self.assertEqual(first.id, second.id)
        self.assertEqual(second.name, "Updated Name")

        row_count = self.connection.execute(
            "SELECT COUNT(*) FROM chains WHERE chain_code = ?",
            ("729006",),
        ).fetchone()[0]
        self.assertEqual(row_count, 1)

    def test_get_by_chain_code_returns_chain_on_hit(self) -> None:
        inserted = self.repository.upsert(Chain(id=None, chain_code="729007", name="Budget Shop"))

        found = self.repository.get_by_chain_code("729007")

        self.assertEqual(found, inserted)

    def test_get_by_chain_code_returns_none_on_miss(self) -> None:
        self.assertIsNone(self.repository.get_by_chain_code("missing-code"))

    def test_get_by_id_returns_chain_on_hit(self) -> None:
        inserted = self.repository.upsert(Chain(id=None, chain_code="729008", name="City Market"))

        found = self.repository.get_by_id(inserted.id)

        self.assertEqual(found, inserted)

    def test_get_by_id_returns_none_on_miss(self) -> None:
        self.assertIsNone(self.repository.get_by_id(9999))


class TestStoreRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = ConnectionFactory.create_connection(":memory:")
        create_schema(self.connection)
        self.chain_repository = ChainRepository(self.connection)
        self.repository = StoreRepository(self.connection)
        self.chain = self.chain_repository.upsert(
            Chain(id=None, chain_code="729020", name="Mega Chain")
        )
        self.other_chain = self.chain_repository.upsert(
            Chain(id=None, chain_code="729021", name="Other Chain")
        )

    def tearDown(self) -> None:
        self.connection.close()

    def _make_store(
        self,
        *,
        chain_id: int,
        store_code: str,
        name: str,
        city: str | None = None,
        address: str | None = None,
        is_active: bool = True,
    ) -> Store:
        return Store(
            id=None,
            chain_id=chain_id,
            store_code=store_code,
            name=name,
            city=city,
            address=address,
            is_active=is_active,
        )

    def test_upsert_inserts_new_store(self) -> None:
        persisted = self.repository.upsert(
            self._make_store(
                chain_id=self.chain.id,
                store_code="001",
                name="Main Branch",
                city="Tel Aviv",
                address="1 Herzl St",
            )
        )

        self.assertIsNotNone(persisted.id)
        self.assertEqual(persisted.chain_id, self.chain.id)
        self.assertEqual(persisted.store_code, "001")
        self.assertEqual(persisted.name, "Main Branch")

    def test_upsert_updates_existing_store_identity_within_chain(self) -> None:
        first = self.repository.upsert(
            self._make_store(
                chain_id=self.chain.id,
                store_code="002",
                name="Old Name",
                city="Haifa",
                address="Old Address",
                is_active=True,
            )
        )

        second = self.repository.upsert(
            self._make_store(
                chain_id=self.chain.id,
                store_code="002",
                name="New Name",
                city="Haifa",
                address="New Address",
                is_active=False,
            )
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(second.name, "New Name")
        self.assertEqual(second.address, "New Address")
        self.assertFalse(second.is_active)

        row_count = self.connection.execute(
            "SELECT COUNT(*) FROM stores WHERE chain_id = ? AND store_code = ?",
            (self.chain.id, "002"),
        ).fetchone()[0]
        self.assertEqual(row_count, 1)

    def test_get_by_chain_and_store_code_returns_store_on_hit(self) -> None:
        inserted = self.repository.upsert(
            self._make_store(chain_id=self.chain.id, store_code="003", name="Lookup Branch")
        )

        found = self.repository.get_by_chain_and_store_code(self.chain.id, "003")

        self.assertEqual(found, inserted)

    def test_get_by_chain_and_store_code_returns_none_on_miss(self) -> None:
        self.assertIsNone(self.repository.get_by_chain_and_store_code(self.chain.id, "999"))

    def test_get_by_id_returns_store_on_hit(self) -> None:
        inserted = self.repository.upsert(
            self._make_store(chain_id=self.chain.id, store_code="004", name="By ID Branch")
        )

        found = self.repository.get_by_id(inserted.id)

        self.assertEqual(found, inserted)

    def test_get_by_id_returns_none_on_miss(self) -> None:
        self.assertIsNone(self.repository.get_by_id(9999))

    def test_get_by_chain_id_returns_only_chain_stores_in_deterministic_order(self) -> None:
        self.repository.upsert(
            self._make_store(chain_id=self.chain.id, store_code="020", name="Twenty")
        )
        self.repository.upsert(
            self._make_store(chain_id=self.chain.id, store_code="005", name="Five")
        )
        self.repository.upsert(
            self._make_store(chain_id=self.other_chain.id, store_code="001", name="Other Chain Store")
        )

        chain_stores = self.repository.get_by_chain_id(self.chain.id)

        self.assertEqual([store.store_code for store in chain_stores], ["005", "020"])
        self.assertTrue(all(store.chain_id == self.chain.id for store in chain_stores))

    def test_get_by_chain_id_returns_empty_list_for_chain_without_stores(self) -> None:
        empty_chain = self.chain_repository.upsert(
            Chain(id=None, chain_code="729022", name="No Stores")
        )

        chain_stores = self.repository.get_by_chain_id(empty_chain.id)

        self.assertEqual(chain_stores, [])


if __name__ == "__main__":
    unittest.main()
