"""Repository implementations for SQLite persistence."""

from __future__ import annotations

import sqlite3
from typing import Iterable

from Modules.models.entities import Product


class ProductRepository:
    """Persistence and lookup operations for products."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError("connection must be a sqlite3.Connection")
        self._connection = connection

    def upsert_product(self, product: Product) -> Product:
        """Insert or update a product using barcode uniqueness."""
        if not isinstance(product, Product):
            raise TypeError("product must be a Product")

        row = self._connection.execute(
            "SELECT id FROM products WHERE barcode = ?",
            (product.barcode,),
        ).fetchone()

        if row is None:
            cursor = self._connection.execute(
                """
                INSERT INTO products (barcode, name, normalized_name, brand, unit_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    product.barcode,
                    product.name,
                    product.normalized_name,
                    product.brand,
                    product.unit_name,
                ),
            )
            product_id = int(cursor.lastrowid)
        else:
            product_id = int(row[0])
            self._connection.execute(
                """
                UPDATE products
                SET name = ?, normalized_name = ?, brand = ?, unit_name = ?
                WHERE id = ?
                """,
                (
                    product.name,
                    product.normalized_name,
                    product.brand,
                    product.unit_name,
                    product_id,
                ),
            )

        self._connection.commit()
        return Product(
            id=product_id,
            barcode=product.barcode,
            name=product.name,
            normalized_name=product.normalized_name,
            brand=product.brand,
            unit_name=product.unit_name,
        )

    def get_by_barcode(self, barcode: str) -> Product | None:
        """Return a single product for a barcode, or ``None`` when missing."""
        if not isinstance(barcode, str):
            raise TypeError("barcode must be a string")

        row = self._connection.execute(
            """
            SELECT id, barcode, name, normalized_name, brand, unit_name
            FROM products
            WHERE barcode = ?
            """,
            (barcode.strip(),),
        ).fetchone()
        return self._row_to_product(row) if row is not None else None

    def get_by_normalized_name(self, normalized_name: str) -> list[Product]:
        """Return products matching the exact normalized name."""
        if not isinstance(normalized_name, str):
            raise TypeError("normalized_name must be a string")

        rows = self._connection.execute(
            """
            SELECT id, barcode, name, normalized_name, brand, unit_name
            FROM products
            WHERE normalized_name = ?
            ORDER BY id ASC
            """,
            (normalized_name.strip(),),
        ).fetchall()
        return [self._row_to_product(row) for row in rows]

    def get_by_ids(self, product_ids: Iterable[int]) -> list[Product]:
        """Return products whose IDs are present in ``product_ids``."""
        ids = [int(product_id) for product_id in product_ids]
        if not ids:
            return []

        placeholders = ",".join("?" for _ in ids)
        rows = self._connection.execute(
            f"""
            SELECT id, barcode, name, normalized_name, brand, unit_name
            FROM products
            WHERE id IN ({placeholders})
            ORDER BY id ASC
            """,
            ids,
        ).fetchall()
        return [self._row_to_product(row) for row in rows]

    @staticmethod
    def _row_to_product(row: sqlite3.Row | tuple[object, ...]) -> Product:
        return Product(
            id=int(row[0]),
            barcode=str(row[1]),
            name=str(row[2]),
            normalized_name=str(row[3]),
            brand=None if row[4] is None else str(row[4]),
            unit_name=None if row[5] is None else str(row[5]),
        )
