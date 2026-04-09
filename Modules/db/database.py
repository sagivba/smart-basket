"""SQLite connection and schema management for the MVP."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class ConnectionFactory:
    """Factory for creating SQLite connections with FK enforcement enabled."""

    @staticmethod
    def create_connection(database_path: str = ":memory:") -> sqlite3.Connection:
        """Create a SQLite connection and enable foreign key enforcement."""
        connection = sqlite3.connect(database_path)
        connection.execute("PRAGMA foreign_keys = ON;")
        return connection


def create_schema(connection: sqlite3.Connection) -> None:
    """Create the MVP database schema and required indexes."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            barcode TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            brand TEXT,
            unit_name TEXT
        );

        CREATE TABLE IF NOT EXISTS chains (
            id INTEGER PRIMARY KEY,
            chain_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY,
            chain_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            name TEXT NOT NULL,
            city TEXT,
            address TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (chain_id) REFERENCES chains(id),
            UNIQUE(chain_id, store_code)
        );

        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            chain_id INTEGER NOT NULL,
            store_id INTEGER NOT NULL,
            price NUMERIC NOT NULL,
            currency TEXT NOT NULL,
            price_date TEXT NOT NULL,
            source_file TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (chain_id) REFERENCES chains(id),
            FOREIGN KEY (store_id) REFERENCES stores(id)
        );

        CREATE TABLE IF NOT EXISTS basket_items (
            id INTEGER PRIMARY KEY,
            basket_id INTEGER NOT NULL,
            product_id INTEGER,
            input_value TEXT NOT NULL,
            input_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            match_status TEXT NOT NULL,
            candidate_product_ids TEXT NOT NULL DEFAULT '[]',
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE INDEX IF NOT EXISTS idx_products_normalized_name
            ON products(normalized_name);

        CREATE INDEX IF NOT EXISTS idx_stores_chain_id
            ON stores(chain_id);

        CREATE INDEX IF NOT EXISTS idx_prices_product_chain
            ON prices(product_id, chain_id);

        CREATE INDEX IF NOT EXISTS idx_prices_store_id
            ON prices(store_id);

        CREATE INDEX IF NOT EXISTS idx_basket_items_basket_id
            ON basket_items(basket_id);

        CREATE INDEX IF NOT EXISTS idx_basket_items_product_id
            ON basket_items(product_id);
        """
    )
    _ensure_basket_item_candidate_column(connection)


def _ensure_basket_item_candidate_column(connection: sqlite3.Connection) -> None:
    """Ensure basket_items includes candidate_product_ids for ambiguous name matches."""
    columns = connection.execute("PRAGMA table_info(basket_items)").fetchall()
    existing_column_names = {str(row[1]) for row in columns}
    if "candidate_product_ids" in existing_column_names:
        return
    connection.execute(
        "ALTER TABLE basket_items ADD COLUMN candidate_product_ids TEXT NOT NULL DEFAULT '[]'"
    )


class DatabaseManager:
    """Coordinates SQLite connection creation and schema initialization."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)

    def get_connection(self) -> sqlite3.Connection:
        """Create and return a connection for the configured database path."""
        return ConnectionFactory.create_connection(self.database_path)

    def initialize_database(self) -> None:
        """Create schema objects for the configured database."""
        with self.get_connection() as connection:
            create_schema(connection)
