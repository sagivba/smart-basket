"""Repository implementations for SQLite persistence."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from Modules.models.entities import Price


class PriceRepository:
    """Persistence operations for product prices."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError("connection must be a sqlite3.Connection")
        self._connection = connection

    def upsert_price(self, price: Price) -> Price:
        """Insert or update a price row using MVP uniqueness keys.

        Uniqueness rule: (product_id, chain_id, store_id, price_date).
        """
        if not isinstance(price, Price):
            raise TypeError("price must be a Price entity")

        cursor = self._connection.cursor()
        cursor.execute(
            """
            UPDATE prices
               SET price = ?,
                   currency = ?,
                   source_file = ?
             WHERE product_id = ?
               AND chain_id = ?
               AND store_id = ?
               AND price_date = ?
            """,
            (
                str(price.price),
                price.currency,
                price.source_file,
                price.product_id,
                price.chain_id,
                price.store_id,
                price.price_date.isoformat(),
            ),
        )

        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO prices (
                    product_id,
                    chain_id,
                    store_id,
                    price,
                    currency,
                    price_date,
                    source_file
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    price.product_id,
                    price.chain_id,
                    price.store_id,
                    str(price.price),
                    price.currency,
                    price.price_date.isoformat(),
                    price.source_file,
                ),
            )
            row_id = cursor.lastrowid
        else:
            cursor.execute(
                """
                SELECT id
                  FROM prices
                 WHERE product_id = ?
                   AND chain_id = ?
                   AND store_id = ?
                   AND price_date = ?
                """,
                (
                    price.product_id,
                    price.chain_id,
                    price.store_id,
                    price.price_date.isoformat(),
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise sqlite3.IntegrityError("Price upsert failed to resolve row id")
            row_id = int(row[0])

        self._connection.commit()
        return Price(
            id=row_id,
            product_id=price.product_id,
            chain_id=price.chain_id,
            store_id=price.store_id,
            price=price.price,
            currency=price.currency,
            price_date=price.price_date,
            source_file=price.source_file,
        )

    def get_by_product_and_chain(self, product_id: int, chain_id: int) -> Price | None:
        """Return representative chain price for a product.

        MVP representative rule: minimum available price across stores in a chain.
        """
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, product_id, chain_id, store_id, price, currency, price_date, source_file
              FROM prices
             WHERE product_id = ?
               AND chain_id = ?
             ORDER BY CAST(price AS REAL) ASC, id ASC
             LIMIT 1
            """,
            (product_id, chain_id),
        )
        row = cursor.fetchone()
        return self._map_price_row(row) if row else None

    def get_prices_for_products_by_chain(
        self,
        product_ids: Sequence[int],
        chain_id: int,
    ) -> dict[int, Price]:
        """Return representative prices for requested products in one chain."""
        if not product_ids:
            return {}

        unique_product_ids = sorted(set(product_ids))
        placeholders = ", ".join("?" for _ in unique_product_ids)

        cursor = self._connection.cursor()
        cursor.execute(
            f"""
            SELECT p.id,
                   p.product_id,
                   p.chain_id,
                   p.store_id,
                   p.price,
                   p.currency,
                   p.price_date,
                   p.source_file
              FROM prices p
              JOIN (
                    SELECT product_id, MIN(CAST(price AS REAL)) AS min_price
                      FROM prices
                     WHERE chain_id = ?
                       AND product_id IN ({placeholders})
                     GROUP BY product_id
                   ) mins
                ON mins.product_id = p.product_id
               AND CAST(p.price AS REAL) = mins.min_price
             WHERE p.chain_id = ?
             ORDER BY p.product_id ASC, p.id ASC
            """,
            [chain_id, *unique_product_ids, chain_id],
        )

        result: dict[int, Price] = {}
        for row in cursor.fetchall():
            mapped = self._map_price_row(row)
            if mapped.product_id not in result:
                result[mapped.product_id] = mapped

        return result

    @staticmethod
    def _map_price_row(row: tuple[object, ...]) -> Price:
        return Price(
            id=int(row[0]),
            product_id=int(row[1]),
            chain_id=int(row[2]),
            store_id=int(row[3]),
            price=Decimal(str(row[4])),
            currency=str(row[5]),
            price_date=date.fromisoformat(str(row[6])),
            source_file=None if row[7] is None else str(row[7]),
        )
