"""Unit tests for database repositories."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import sqlite3
import tempfile
import unittest
from pathlib import Path

from Modules.db.database import ConnectionFactory, DatabaseManager, create_schema
from Modules.db.repositories import BasketRepository, DataImportRepository, PriceRepository
from Modules.models.entities import BasketItem, Price


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


class TestChainRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "chains.db"
        self.connection = sqlite3.connect(str(self.database_path))
        create_schema(self.connection)
        self.repository = ChainRepository(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.temp_dir.cleanup()

    def test_upsert_chain_inserts_then_updates_by_chain_code(self) -> None:
        created = self.repository.upsert_chain(Chain(id=None, chain_code="C-001", name="Chain One"))
        updated = self.repository.upsert_chain(
            Chain(id=None, chain_code="C-001", name="Chain One Renamed")
        )

        self.assertEqual(created.id, updated.id)
        self.assertEqual(updated.name, "Chain One Renamed")

        row_count = self.connection.execute(
            "SELECT COUNT(*) FROM chains WHERE chain_code = 'C-001'"
        ).fetchone()[0]
        self.assertEqual(row_count, 1)

    def test_get_by_id_returns_chain_or_none(self) -> None:
        created = self.repository.upsert_chain(Chain(id=None, chain_code="C-002", name="Chain Two"))

        found = self.repository.get_by_id(created.id)
        missing = self.repository.get_by_id(9999)

        self.assertIsNotNone(found)
        self.assertEqual(found.chain_code, "C-002")
        self.assertIsNone(missing)

    def test_get_by_chain_code_returns_chain_or_none(self) -> None:
        self.repository.upsert_chain(Chain(id=None, chain_code="C-003", name="Chain Three"))

        found = self.repository.get_by_chain_code("C-003")
        missing = self.repository.get_by_chain_code("UNKNOWN")

        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Chain Three")
        self.assertIsNone(missing)


class TestStoreRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "stores.db"
        self.connection = sqlite3.connect(str(self.database_path))
        create_schema(self.connection)
        self.chain_repository = ChainRepository(self.connection)
        self.repository = StoreRepository(self.connection)

        self.chain_a = self.chain_repository.upsert_chain(
            Chain(id=None, chain_code="CHAIN-A", name="Chain A")
        )
        self.chain_b = self.chain_repository.upsert_chain(
            Chain(id=None, chain_code="CHAIN-B", name="Chain B")
        )

    def tearDown(self) -> None:
        self.connection.close()
        self.temp_dir.cleanup()

    def test_upsert_store_inserts_then_updates_by_chain_and_store_code(self) -> None:
        created = self.repository.upsert_store(
            Store(
                id=None,
                chain_id=self.chain_a.id,
                store_code="A-1",
                name="Store A1",
                city="Tel Aviv",
                address="Street 1",
                is_active=True,
            )
        )
        updated = self.repository.upsert_store(
            Store(
                id=None,
                chain_id=self.chain_a.id,
                store_code="A-1",
                name="Store A1 Updated",
                city="Haifa",
                address="Street 99",
                is_active=False,
            )
        )

        self.assertEqual(created.id, updated.id)
        self.assertFalse(updated.is_active)

        row = self.connection.execute(
            "SELECT name, city, address, is_active FROM stores WHERE id = ?",
            (updated.id,),
        ).fetchone()
        self.assertEqual(row, ("Store A1 Updated", "Haifa", "Street 99", 0))

    def test_get_by_id_returns_store_or_none(self) -> None:
        created = self.repository.upsert_store(
            Store(
                id=None,
                chain_id=self.chain_a.id,
                store_code="A-2",
                name="Store A2",
            )
        )

        found = self.repository.get_by_id(created.id)
        missing = self.repository.get_by_id(9999)

        self.assertIsNotNone(found)
        self.assertEqual(found.store_code, "A-2")
        self.assertTrue(found.is_active)
        self.assertIsNone(missing)

    def test_get_by_chain_and_store_code_returns_store_or_none(self) -> None:
        self.repository.upsert_store(
            Store(
                id=None,
                chain_id=self.chain_a.id,
                store_code="A-3",
                name="Store A3",
            )
        )

        found = self.repository.get_by_chain_and_store_code(self.chain_a.id, "A-3")
        missing = self.repository.get_by_chain_and_store_code(self.chain_b.id, "A-3")

        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Store A3")
        self.assertIsNone(missing)

    def test_get_stores_by_chain_returns_only_requested_chain_in_id_order(self) -> None:
        store_a2 = self.repository.upsert_store(
            Store(
                id=None,
                chain_id=self.chain_a.id,
                store_code="A-2",
                name="Store A2",
            )
        )
        store_a1 = self.repository.upsert_store(
            Store(
                id=None,
                chain_id=self.chain_a.id,
                store_code="A-1",
                name="Store A1",
            )
        )
        self.repository.upsert_store(
            Store(
                id=None,
                chain_id=self.chain_b.id,
                store_code="B-1",
                name="Store B1",
            )
        )

        stores = self.repository.get_stores_by_chain(self.chain_a.id)

        self.assertEqual([store.id for store in stores], [store_a2.id, store_a1.id])
        self.assertTrue(all(store.chain_id == self.chain_a.id for store in stores))



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


    def test_update_item_raises_when_identifier_missing(self) -> None:
        item_without_id = BasketItem(
            id=None,
            basket_id=300,
            product_id=21,
            input_value="milk",
            input_type="name",
            quantity=1,
            match_status="matched",
        )

        with self.assertRaisesRegex(ValueError, "item.id is required for update"):
            self.repository.update_item(item_without_id)

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

    def test_clear_by_basket_id_removes_all_items_for_one_basket(self) -> None:
        self.repository.add_item(
            self._make_item(
                basket_id=600,
                product_id=51,
                input_value="basket-600-a",
                input_type="name",
                quantity=1,
                match_status="matched",
            )
        )
        self.repository.add_item(
            self._make_item(
                basket_id=600,
                product_id=52,
                input_value="basket-600-b",
                input_type="name",
                quantity=2,
                match_status="matched",
            )
        )
        self.repository.add_item(
            self._make_item(
                basket_id=601,
                product_id=53,
                input_value="basket-601-a",
                input_type="name",
                quantity=1,
                match_status="matched",
            )
        )

        deleted_count = self.repository.clear_by_basket_id(600)

        self.assertEqual(deleted_count, 2)
        self.assertEqual(self.repository.get_by_basket_id(600), [])
        self.assertEqual(len(self.repository.get_by_basket_id(601)), 1)


class TestDataImportRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        create_schema(self.connection)
        self.repository = DataImportRepository(self.connection)

    def tearDown(self) -> None:
        self.connection.close()

    def test_upsert_product_persists_and_updates_by_barcode(self) -> None:
        self.repository.upsert_product(
            barcode="123",
            name="Milk",
            normalized_name="milk",
            brand="BrandA",
            unit_name="1L",
        )
        self.repository.upsert_product(
            barcode="123",
            name="Milk Updated",
            normalized_name="milk updated",
            brand=None,
            unit_name=None,
        )

        row = self.connection.execute(
            "SELECT barcode, name, normalized_name, brand, unit_name FROM products WHERE barcode = ?",
            ("123",),
        ).fetchone()
        self.assertEqual(row, ("123", "Milk Updated", "milk updated", None, None))

    def test_upsert_chain_and_store_supports_loader_lookup_flow(self) -> None:
        chain_id = self.repository.upsert_chain(chain_code="CH1", name="Chain One")
        self.repository.upsert_store(
            chain_id=chain_id,
            store_code="S1",
            name="Store One",
            city="City",
            address="Address",
            is_active=True,
        )

        loaded_chain_id = self.repository.get_chain_id_by_code("CH1")
        loaded_store_id = self.repository.get_store_id(chain_id=loaded_chain_id, store_code="S1")

        self.assertEqual(loaded_chain_id, chain_id)
        self.assertGreater(loaded_store_id, 0)


class TestPriceRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "prices.db"
        self.connection = sqlite3.connect(str(self.database_path))
        create_schema(self.connection)
        self.repository = PriceRepository(self.connection)
        self._seed_reference_data()

    def tearDown(self) -> None:
        self.connection.close()
        self.temp_dir.cleanup()

    def _seed_reference_data(self) -> None:
        self.connection.execute(
            """
            INSERT INTO products (id, barcode, name, normalized_name, brand, unit_name)
            VALUES
                (1, '111', 'Milk', 'milk', NULL, NULL),
                (2, '222', 'Bread', 'bread', NULL, NULL)
            """
        )
        self.connection.execute(
            """
            INSERT INTO chains (id, chain_code, name)
            VALUES
                (10, 'CHAIN-A', 'Chain A'),
                (20, 'CHAIN-B', 'Chain B')
            """
        )
        self.connection.execute(
            """
            INSERT INTO stores (id, chain_id, store_code, name, city, address, is_active)
            VALUES
                (100, 10, 'A-1', 'Store A1', NULL, NULL, 1),
                (101, 10, 'A-2', 'Store A2', NULL, NULL, 1),
                (102, 10, 'A-3', 'Store A3', NULL, NULL, 1),
                (200, 20, 'B-1', 'Store B1', NULL, NULL, 1)
            """
        )
        self.connection.commit()

    def _make_price(
        self,
        *,
        product_id: int,
        chain_id: int,
        store_id: int,
        price: str,
        currency: str = "ILS",
        price_date: date = date(2026, 4, 1),
        source_file: str | None = "prices.csv",
    ) -> Price:
        return Price(
            id=None,
            product_id=product_id,
            chain_id=chain_id,
            store_id=store_id,
            price=Decimal(price),
            currency=currency,
            price_date=price_date,
            source_file=source_file,
        )

    def test_upsert_price_inserts_then_updates_same_mvp_natural_key(self) -> None:
        created = self.repository.upsert_price(
            self._make_price(product_id=1, chain_id=10, store_id=100, price="8.30")
        )
        updated = self.repository.upsert_price(
            self._make_price(product_id=1, chain_id=10, store_id=100, price="7.95")
        )

        self.assertIsNotNone(created.id)
        self.assertEqual(created.id, updated.id)
        self.assertEqual(updated.price, Decimal("7.95"))

        row_count = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM prices
            WHERE product_id = 1 AND chain_id = 10 AND store_id = 100
              AND currency = 'ILS' AND price_date = '2026-04-01'
            """
        ).fetchone()[0]
        persisted_price = self.connection.execute(
            "SELECT price FROM prices WHERE id = ?",
            (updated.id,),
        ).fetchone()[0]
        self.assertEqual(row_count, 1)
        self.assertEqual(Decimal(str(persisted_price)), Decimal("7.95"))

    def test_get_price_by_product_and_chain_returns_chain_minimum_price(self) -> None:
        self.repository.upsert_price(
            self._make_price(product_id=1, chain_id=10, store_id=100, price="10.00")
        )
        self.repository.upsert_price(
            self._make_price(product_id=1, chain_id=10, store_id=101, price="9.10")
        )
        self.repository.upsert_price(
            self._make_price(product_id=1, chain_id=10, store_id=102, price="9.10")
        )

        representative_price = self.repository.get_price_by_product_and_chain(1, 10)

        self.assertIsNotNone(representative_price)
        self.assertEqual(representative_price.price, Decimal("9.10"))
        self.assertEqual(
            representative_price.store_id,
            101,
            "tie-break remains deterministic by lower store_id",
        )

    def test_get_price_by_product_and_chain_returns_none_when_missing(self) -> None:
        representative_price = self.repository.get_price_by_product_and_chain(1, 10)
        self.assertIsNone(representative_price)

    def test_get_prices_for_products_by_chain_returns_representative_price_map(self) -> None:
        self.repository.upsert_price(
            self._make_price(product_id=1, chain_id=10, store_id=100, price="9.90")
        )
        self.repository.upsert_price(
            self._make_price(product_id=1, chain_id=10, store_id=101, price="9.50")
        )
        self.repository.upsert_price(
            self._make_price(product_id=2, chain_id=10, store_id=100, price="5.20")
        )
        self.repository.upsert_price(
            self._make_price(product_id=1, chain_id=20, store_id=200, price="10.30")
        )

        prices_map = self.repository.get_prices_for_products_by_chain(
            product_ids=[2, 1],
            chain_ids=[20, 10],
        )

        self.assertEqual(prices_map[10][1].price, Decimal("9.50"))
        self.assertEqual(prices_map[10][2].price, Decimal("5.20"))
        self.assertEqual(prices_map[20][1].price, Decimal("10.30"))
        self.assertNotIn(2, prices_map[20], "missing prices stay absent from mapping")

    def test_get_prices_for_products_by_chain_returns_empty_for_empty_input(self) -> None:
        self.assertEqual(
            self.repository.get_prices_for_products_by_chain(product_ids=[], chain_ids=[10]),
            {},
        )
        self.assertEqual(
            self.repository.get_prices_for_products_by_chain(product_ids=[1], chain_ids=[]),
            {},
        )


if __name__ == "__main__":
    unittest.main()
