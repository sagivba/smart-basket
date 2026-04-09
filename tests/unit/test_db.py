"""Unit tests for SQLite connection and schema initialization."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from Modules.db.database import ConnectionFactory, DatabaseManager, create_schema


class TestConnectionFactory(unittest.TestCase):
    def test_create_connection_returns_sqlite_connection(self) -> None:
        connection = ConnectionFactory.create_connection(":memory:")
        try:
            self.assertIsInstance(connection, sqlite3.Connection)
        finally:
            connection.close()

    def test_create_connection_enables_foreign_keys(self) -> None:
        connection = ConnectionFactory.create_connection(":memory:")
        try:
            row = connection.execute("PRAGMA foreign_keys;").fetchone()
            self.assertEqual((1,), row)
        finally:
            connection.close()


class TestSchemaCreation(unittest.TestCase):
    EXPECTED_TABLES = {"products", "chains", "stores", "prices", "basket_items"}
    EXPECTED_INDEXES = {
        "idx_products_normalized_name",
        "idx_stores_chain_id",
        "idx_prices_product_chain",
        "idx_prices_store_id",
        "idx_basket_items_basket_id",
        "idx_basket_items_product_id",
    }

    def setUp(self) -> None:
        self.connection = ConnectionFactory.create_connection(":memory:")

    def tearDown(self) -> None:
        self.connection.close()

    def test_create_schema_succeeds(self) -> None:
        create_schema(self.connection)
        self.connection.execute("SELECT 1;").fetchone()

    def test_create_schema_is_idempotent(self) -> None:
        create_schema(self.connection)
        create_schema(self.connection)

        tables = self._get_table_names()
        self.assertTrue(self.EXPECTED_TABLES.issubset(tables))

    def test_expected_tables_are_created(self) -> None:
        create_schema(self.connection)

        tables = self._get_table_names()
        self.assertSetEqual(self.EXPECTED_TABLES, tables)

    def test_expected_indexes_exist(self) -> None:
        create_schema(self.connection)

        index_names = self._get_index_names()
        self.assertTrue(self.EXPECTED_INDEXES.issubset(index_names))

    def _get_table_names(self) -> set[str]:
        rows = self.connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name IN ('products', 'chains', 'stores', 'prices', 'basket_items');
            """
        ).fetchall()
        return {name for (name,) in rows}

    def _get_index_names(self) -> set[str]:
        rows = self.connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'index'
              AND name IN (
                'idx_products_normalized_name',
                'idx_stores_chain_id',
                'idx_prices_product_chain',
                'idx_prices_store_id',
                'idx_basket_items_basket_id',
                'idx_basket_items_product_id'
              );
            """
        ).fetchall()
        return {name for (name,) in rows}


class TestDatabaseManager(unittest.TestCase):
    def test_get_connection_uses_configured_database_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "basket.sqlite"
            manager = DatabaseManager(db_path)

            connection = manager.get_connection()
            try:
                connection.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY);")
            finally:
                connection.close()

            self.assertTrue(db_path.exists())

    def test_initialize_database_creates_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "basket.sqlite"
            manager = DatabaseManager(db_path)

            manager.initialize_database()

            verify_connection = sqlite3.connect(str(db_path))
            try:
                rows = verify_connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                      AND name = 'products';
                    """
                ).fetchall()
                self.assertEqual([("products",)], rows)
            finally:
                verify_connection.close()


if __name__ == "__main__":
    unittest.main()
