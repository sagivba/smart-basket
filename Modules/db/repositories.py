"""SQLite repository implementations for MVP persistence operations."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from Modules.models.entities import BasketItem, Price


class DataImportRepository:
    """Persistence operations used by data-loading orchestration."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def replace_products(self) -> None:
        """Delete all rows from products for deterministic replace loads."""
        self._connection.execute("DELETE FROM products")

    def upsert_product(
        self,
        *,
        barcode: str,
        name: str,
        normalized_name: str,
        brand: str | None,
        unit_name: str | None,
    ) -> None:
        """Insert or update one product row by barcode."""
        self._connection.execute(
            """
            INSERT INTO products (barcode, name, normalized_name, brand, unit_name)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(barcode)
            DO UPDATE SET
                name = excluded.name,
                normalized_name = excluded.normalized_name,
                brand = excluded.brand,
                unit_name = excluded.unit_name
            """,
            (barcode, name, normalized_name, brand, unit_name),
        )

    def replace_stores(self) -> None:
        """Delete all rows from stores for deterministic replace loads."""
        self._connection.execute("DELETE FROM stores")

    def upsert_chain(self, *, chain_code: str, name: str) -> int:
        """Insert or update one chain and return its identifier."""
        self._connection.execute(
            """
            INSERT INTO chains (chain_code, name)
            VALUES (?, ?)
            ON CONFLICT(chain_code)
            DO UPDATE SET name = excluded.name
            """,
            (chain_code, name),
        )
        row = self._connection.execute(
            "SELECT id FROM chains WHERE chain_code = ?",
            (chain_code,),
        ).fetchone()
        if row is None:
            raise ValueError(f"missing chain after upsert: {chain_code}")
        return int(row[0])

    def upsert_store(
        self,
        *,
        chain_id: int,
        store_code: str,
        name: str,
        city: str | None,
        address: str | None,
        is_active: bool,
    ) -> None:
        """Insert or update one store row by (chain_id, store_code)."""
        self._connection.execute(
            """
            INSERT INTO stores (chain_id, store_code, name, city, address, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(chain_id, store_code)
            DO UPDATE SET
                name = excluded.name,
                city = excluded.city,
                address = excluded.address,
                is_active = excluded.is_active
            """,
            (chain_id, store_code, name, city, address, 1 if is_active else 0),
        )

    def replace_prices(self) -> None:
        """Delete all rows from prices for deterministic replace loads."""
        self._connection.execute("DELETE FROM prices")

    def get_product_id_by_barcode(self, barcode: str) -> int:
        """Return product id for a barcode or raise when missing."""
        row = self._connection.execute(
            "SELECT id FROM products WHERE barcode = ?",
            (barcode,),
        ).fetchone()
        if row is None:
            raise ValueError(f"product not found for barcode={barcode}")
        return int(row[0])

    def get_chain_id_by_code(self, chain_code: str) -> int:
        """Return chain id for a chain code or raise when missing."""
        row = self._connection.execute(
            "SELECT id FROM chains WHERE chain_code = ?",
            (chain_code,),
        ).fetchone()
        if row is None:
            raise ValueError(f"chain not found for chain_code={chain_code}")
        return int(row[0])

    def get_store_id(self, *, chain_id: int, store_code: str) -> int:
        """Return store id for a chain/store code pair or raise when missing."""
        row = self._connection.execute(
            "SELECT id FROM stores WHERE chain_id = ? AND store_code = ?",
            (chain_id, store_code),
        ).fetchone()
        if row is None:
            raise ValueError(f"store not found for chain_id={chain_id}, store_code={store_code}")
        return int(row[0])

    def insert_price(
        self,
        *,
        product_id: int,
        chain_id: int,
        store_id: int,
        price: str,
        currency: str,
        price_date: str,
        source_file: str,
    ) -> None:
        """Insert one price row."""
        self._connection.execute(
            """
            INSERT INTO prices (product_id, chain_id, store_id, price, currency, price_date, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (product_id, chain_id, store_id, price, currency, price_date, source_file),
        )


class PriceRepository:
    """Persistence and retrieval operations for product prices."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def upsert_price(self, price: Price) -> Price:
        """Insert or update a price row by its current MVP natural key."""
        existing_row = self._connection.execute(
            """
            SELECT id
            FROM prices
            WHERE product_id = ?
              AND chain_id = ?
              AND store_id = ?
              AND currency = ?
              AND price_date = ?
            """,
            (
                price.product_id,
                price.chain_id,
                price.store_id,
                price.currency,
                price.price_date.isoformat(),
            ),
        ).fetchone()

        if existing_row is None:
            cursor = self._connection.execute(
                """
                INSERT INTO prices (
                    product_id,
                    chain_id,
                    store_id,
                    price,
                    currency,
                    price_date,
                    source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
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
            persisted_id = int(cursor.lastrowid)
        else:
            persisted_id = int(existing_row[0])
            self._connection.execute(
                """
                UPDATE prices
                SET price = ?,
                    source_file = ?
                WHERE id = ?
                """,
                (str(price.price), price.source_file, persisted_id),
            )

        self._connection.commit()
        return Price(
            id=persisted_id,
            product_id=price.product_id,
            chain_id=price.chain_id,
            store_id=price.store_id,
            price=price.price,
            currency=price.currency,
            price_date=price.price_date,
            source_file=price.source_file,
        )

    def get_price_by_product_and_chain(self, product_id: int, chain_id: int) -> Price | None:
        """Return the current MVP representative chain price for one product.

        MVP assumption: when no store is selected, representative chain price is
        the minimum available store price for the product inside that chain.
        """
        row = self._connection.execute(
            """
            SELECT id, product_id, chain_id, store_id, price, currency, price_date, source_file
            FROM prices
            WHERE product_id = ? AND chain_id = ?
            ORDER BY CAST(price AS REAL) ASC, store_id ASC, id ASC
            LIMIT 1
            """,
            (product_id, chain_id),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_price(row)

    def get_prices_for_products_by_chain(
        self, product_ids: list[int], chain_ids: list[int]
    ) -> dict[int, dict[int, Price]]:
        """Return representative prices keyed by chain then product.

        Missing prices are represented by absent product keys in each chain map.
        """
        if not product_ids or not chain_ids:
            return {}

        products_placeholders = ",".join(["?"] * len(product_ids))
        chains_placeholders = ",".join(["?"] * len(chain_ids))

        rows = self._connection.execute(
            f"""
            SELECT id, product_id, chain_id, store_id, price, currency, price_date, source_file
            FROM prices
            WHERE product_id IN ({products_placeholders})
              AND chain_id IN ({chains_placeholders})
            ORDER BY chain_id ASC, product_id ASC, CAST(price AS REAL) ASC, store_id ASC, id ASC
            """,
            [*product_ids, *chain_ids],
        ).fetchall()

        prices_by_chain: dict[int, dict[int, Price]] = {}
        for row in rows:
            price = self._row_to_price(row)
            chain_prices = prices_by_chain.setdefault(price.chain_id, {})
            if price.product_id not in chain_prices:
                chain_prices[price.product_id] = price

        return prices_by_chain

    @staticmethod
    def _row_to_price(row: sqlite3.Row | tuple[object, ...]) -> Price:
        """Map one `prices` row into a Price entity."""
        return Price(
            id=int(row[0]),
            product_id=int(row[1]),
            chain_id=int(row[2]),
            store_id=int(row[3]),
            price=Decimal(str(row[4])),
            currency=str(row[5]),
            price_date=date.fromisoformat(str(row[6])),
            source_file=row[7],
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

    def clear_by_basket_id(self, basket_id: int) -> int:
        """Delete all basket items in one basket and return number of deleted rows."""
        cursor = self._connection.execute(
            "DELETE FROM basket_items WHERE basket_id = ?",
            (basket_id,),
        )
        self._connection.commit()
        return cursor.rowcount

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
