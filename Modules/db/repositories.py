"""Repository implementations for database persistence operations."""

from __future__ import annotations

import sqlite3
from typing import Optional

from Modules.models.entities import Chain, Store


class ChainRepository:
    """Persistence operations for ``Chain`` entities."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def upsert_chain(self, chain: Chain) -> Chain:
        """Insert or update a chain using ``chain_code`` as the uniqueness rule."""
        existing = self.get_by_chain_code(chain.chain_code)

        if existing is None:
            cursor = self._connection.execute(
                """
                INSERT INTO chains (chain_code, name)
                VALUES (?, ?)
                """,
                (chain.chain_code, chain.name),
            )
            self._connection.commit()
            return Chain(id=int(cursor.lastrowid), chain_code=chain.chain_code, name=chain.name)

        self._connection.execute(
            """
            UPDATE chains
            SET name = ?
            WHERE id = ?
            """,
            (chain.name, existing.id),
        )
        self._connection.commit()
        return Chain(id=existing.id, chain_code=chain.chain_code, name=chain.name)

    def get_by_chain_code(self, chain_code: str) -> Optional[Chain]:
        """Return a chain by chain code, or ``None`` when not found."""
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

        return Chain(id=row[0], chain_code=row[1], name=row[2])


class StoreRepository:
    """Persistence operations for ``Store`` entities."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def upsert_store(self, store: Store) -> Store:
        """Insert or update a store using ``(chain_id, store_code)`` as uniqueness rule."""
        existing = self.get_by_chain_and_store_code(store.chain_id, store.store_code)

        if existing is None:
            cursor = self._connection.execute(
                """
                INSERT INTO stores (chain_id, store_code, name, city, address, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
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
            self._connection.commit()
            return Store(
                id=int(cursor.lastrowid),
                chain_id=store.chain_id,
                store_code=store.store_code,
                name=store.name,
                city=store.city,
                address=store.address,
                is_active=store.is_active,
            )

        self._connection.execute(
            """
            UPDATE stores
            SET name = ?, city = ?, address = ?, is_active = ?
            WHERE id = ?
            """,
            (
                store.name,
                store.city,
                store.address,
                int(store.is_active),
                existing.id,
            ),
        )
        self._connection.commit()
        return Store(
            id=existing.id,
            chain_id=store.chain_id,
            store_code=store.store_code,
            name=store.name,
            city=store.city,
            address=store.address,
            is_active=store.is_active,
        )

    def get_by_chain_and_store_code(self, chain_id: int, store_code: str) -> Optional[Store]:
        """Return a store for a specific chain/store code pair, or ``None``."""
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

        return self._map_store_row(row)

    def get_by_chain(self, chain_id: int) -> list[Store]:
        """Return all stores for a chain ordered by ID."""
        rows = self._connection.execute(
            """
            SELECT id, chain_id, store_code, name, city, address, is_active
            FROM stores
            WHERE chain_id = ?
            ORDER BY id ASC
            """,
            (chain_id,),
        ).fetchall()

        return [self._map_store_row(row) for row in rows]

    @staticmethod
    def _map_store_row(row: sqlite3.Row | tuple) -> Store:
        """Map a raw stores table row to a ``Store`` entity."""
        return Store(
            id=row[0],
            chain_id=row[1],
            store_code=row[2],
            name=row[3],
            city=row[4],
            address=row[5],
            is_active=bool(row[6]),
        )
