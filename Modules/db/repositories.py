"""SQLite repository implementations for MVP persistence operations."""

from __future__ import annotations

import sqlite3

from Modules.models.entities import BasketItem


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
