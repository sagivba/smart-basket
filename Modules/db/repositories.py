"""SQLite repository implementations for MVP persistence operations."""

from __future__ import annotations

import sqlite3

from Modules.models.entities import BasketItem, Chain, Store


class ChainRepository:
    """Persistence operations for retail chains."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def upsert(self, chain: Chain) -> Chain:
        """Insert or update a chain by chain_code and return the persisted entity."""
        cursor = self._connection.execute(
            """
            INSERT INTO chains (chain_code, name)
            VALUES (?, ?)
            ON CONFLICT(chain_code) DO UPDATE SET
                name = excluded.name
            RETURNING id, chain_code, name
            """,
            (chain.chain_code, chain.name),
        )
        row = cursor.fetchone()
        self._connection.commit()
        return self._row_to_chain(row)

    def get_by_chain_code(self, chain_code: str) -> Chain | None:
        """Return a chain by its chain code."""
        row = self._connection.execute(
            """
            SELECT id, chain_code, name
            FROM chains
            WHERE chain_code = ?
            """,
            (chain_code,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_chain(row)

    def get_by_id(self, chain_id: int) -> Chain | None:
        """Return a chain by its identifier."""
        row = self._connection.execute(
            """
            SELECT id, chain_code, name
            FROM chains
            WHERE id = ?
            """,
            (chain_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_chain(row)

    @staticmethod
    def _row_to_chain(row: sqlite3.Row | tuple[object, ...]) -> Chain:
        """Map a chains row to a Chain entity."""
        return Chain(
            id=row[0],
            chain_code=row[1],
            name=row[2],
        )


class StoreRepository:
    """Persistence operations for stores."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def upsert(self, store: Store) -> Store:
        """Insert or update a store by chain/store identity and return the persisted entity."""
        cursor = self._connection.execute(
            """
            INSERT INTO stores (chain_id, store_code, name, city, address, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(chain_id, store_code) DO UPDATE SET
                name = excluded.name,
                city = excluded.city,
                address = excluded.address,
                is_active = excluded.is_active
            RETURNING id, chain_id, store_code, name, city, address, is_active
            """,
            (
                store.chain_id,
                store.store_code,
                store.name,
                store.city,
                store.address,
                int(store.is_active),
            ),
        )
        row = cursor.fetchone()
        self._connection.commit()
        return self._row_to_store(row)

    def get_by_chain_and_store_code(self, chain_id: int, store_code: str) -> Store | None:
        """Return a store by chain identifier and store code."""
        row = self._connection.execute(
            """
            SELECT id, chain_id, store_code, name, city, address, is_active
            FROM stores
            WHERE chain_id = ? AND store_code = ?
            """,
            (chain_id, store_code),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_store(row)

    def get_by_id(self, store_id: int) -> Store | None:
        """Return a store by identifier."""
        row = self._connection.execute(
            """
            SELECT id, chain_id, store_code, name, city, address, is_active
            FROM stores
            WHERE id = ?
            """,
            (store_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_store(row)

    def get_by_chain_id(self, chain_id: int) -> list[Store]:
        """Return all stores for a chain in a deterministic order."""
        rows = self._connection.execute(
            """
            SELECT id, chain_id, store_code, name, city, address, is_active
            FROM stores
            WHERE chain_id = ?
            ORDER BY store_code, id
            """,
            (chain_id,),
        ).fetchall()
        return [self._row_to_store(row) for row in rows]

    @staticmethod
    def _row_to_store(row: sqlite3.Row | tuple[object, ...]) -> Store:
        """Map a stores row to a Store entity."""
        return Store(
            id=row[0],
            chain_id=row[1],
            store_code=row[2],
            name=row[3],
            city=row[4],
            address=row[5],
            is_active=bool(row[6]),
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
