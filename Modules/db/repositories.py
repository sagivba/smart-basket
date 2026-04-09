"""SQLite repository implementations for MVP persistence operations."""

from __future__ import annotations

import sqlite3

from Modules.models.entities import BasketItem, Product


class ProductRepository:
    """Persistence operations for products."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def upsert_product(self, product: Product) -> Product:
        """Insert or update a product by barcode and return the persisted row."""
        cursor = self._connection.execute(
            """
            INSERT INTO products (barcode, name, normalized_name, brand, unit_name)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(barcode) DO UPDATE SET
                name = excluded.name,
                normalized_name = excluded.normalized_name,
                brand = excluded.brand,
                unit_name = excluded.unit_name
            RETURNING id, barcode, name, normalized_name, brand, unit_name
            """,
            (
                product.barcode,
                product.name,
                product.normalized_name,
                product.brand,
                product.unit_name,
            ),
        )
        row = cursor.fetchone()
        self._connection.commit()
        return self._row_to_product(row)

    def get_by_barcode(self, barcode: str) -> Product | None:
        """Return a single product by exact barcode, if it exists."""
        row = self._connection.execute(
            """
            SELECT id, barcode, name, normalized_name, brand, unit_name
            FROM products
            WHERE barcode = ?
            """,
            (barcode,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_product(row)

    def get_by_normalized_name(self, normalized_name: str) -> list[Product]:
        """Return all products with the exact normalized name."""
        rows = self._connection.execute(
            """
            SELECT id, barcode, name, normalized_name, brand, unit_name
            FROM products
            WHERE normalized_name = ?
            ORDER BY id
            """,
            (normalized_name,),
        ).fetchall()
        return [self._row_to_product(row) for row in rows]

    def get_by_ids(self, product_ids: list[int]) -> list[Product]:
        """Return products for the provided identifiers in deterministic order."""
        if not product_ids:
            return []

        placeholders = ",".join("?" for _ in product_ids)
        rows = self._connection.execute(
            f"""
            SELECT id, barcode, name, normalized_name, brand, unit_name
            FROM products
            WHERE id IN ({placeholders})
            ORDER BY id
            """,
            tuple(product_ids),
        ).fetchall()
        return [self._row_to_product(row) for row in rows]

    @staticmethod
    def _row_to_product(row: sqlite3.Row | tuple[object, ...]) -> Product:
        """Map a row from products to a Product entity."""
        return Product(
            id=row[0],
            barcode=row[1],
            name=row[2],
            normalized_name=row[3],
            brand=row[4],
            unit_name=row[5],
        )


class BasketRepository:
    """Persistence operations for basket items."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add_item(self, item: BasketItem) -> BasketItem:
        """Insert a basket item and return it with the generated identifier."""
        cursor = self._connection.execute(
            """
            INSERT INTO basket_items (
                basket_id,
                product_id,
                input_value,
                input_type,
                quantity,
                match_status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                item.basket_id,
                item.product_id,
                item.input_value,
                item.input_type,
                item.quantity,
                item.match_status,
            ),
        )
        self._connection.commit()

        return BasketItem(
            id=int(cursor.lastrowid),
            basket_id=item.basket_id,
            product_id=item.product_id,
            input_value=item.input_value,
            input_type=item.input_type,
            quantity=item.quantity,
            match_status=item.match_status,
        )

    def get_by_basket_id(self, basket_id: int) -> list[BasketItem]:
        """Return all items that belong to the requested basket identifier."""
        rows = self._connection.execute(
            """
            SELECT id, basket_id, product_id, input_value, input_type, quantity, match_status
            FROM basket_items
            WHERE basket_id = ?
            ORDER BY id
            """,
            (basket_id,),
        )
        return [self._row_to_item(row) for row in rows.fetchall()]

    def update_item(self, item: BasketItem) -> None:
        """Update an existing basket item by identifier."""
        if item.id is None:
            raise ValueError("item.id is required for update")

        self._connection.execute(
            """
            UPDATE basket_items
            SET basket_id = ?,
                product_id = ?,
                input_value = ?,
                input_type = ?,
                quantity = ?,
                match_status = ?
            WHERE id = ?
            """,
            (
                item.basket_id,
                item.product_id,
                item.input_value,
                item.input_type,
                item.quantity,
                item.match_status,
                item.id,
            ),
        )
        self._connection.commit()

    def delete_item(self, item_id: int) -> None:
        """Delete a single basket item by identifier."""
        self._connection.execute("DELETE FROM basket_items WHERE id = ?", (item_id,))
        self._connection.commit()

    @staticmethod
    def _row_to_item(row: sqlite3.Row | tuple[object, ...]) -> BasketItem:
        """Map a row from basket_items to a BasketItem entity."""
        return BasketItem(
            id=row[0],
            basket_id=row[1],
            product_id=row[2],
            input_value=row[3],
            input_type=row[4],
            quantity=row[5],
            match_status=row[6],
        )
