"""Unit tests for DB repositories."""

from __future__ import annotations

import sqlite3
import unittest

from Modules.db.repositories import ChainRepository, StoreRepository
from Modules.models.entities import Chain, Store


class TestChainAndStoreRepositories(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute("PRAGMA foreign_keys = ON")

        self.connection.execute(
            """
            CREATE TABLE chains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE stores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id INTEGER NOT NULL,
                store_code TEXT NOT NULL,
                name TEXT NOT NULL,
                city TEXT,
                address TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                UNIQUE(chain_id, store_code),
                FOREIGN KEY(chain_id) REFERENCES chains(id)
            )
            """
        )

        self.chain_repository = ChainRepository(self.connection)
        self.store_repository = StoreRepository(self.connection)

    def tearDown(self) -> None:
        self.connection.close()

    def test_insert_chain(self) -> None:
        created = self.chain_repository.upsert_chain(Chain(id=None, chain_code="CH01", name="Chain One"))

        self.assertIsNotNone(created.id)
        self.assertEqual(created.chain_code, "CH01")
        self.assertEqual(created.name, "Chain One")

    def test_update_existing_chain_through_upsert(self) -> None:
        self.chain_repository.upsert_chain(Chain(id=None, chain_code="CH01", name="Chain One"))

        updated = self.chain_repository.upsert_chain(
            Chain(id=None, chain_code="CH01", name="Chain One Updated")
        )

        self.assertEqual(updated.chain_code, "CH01")
        self.assertEqual(updated.name, "Chain One Updated")
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM chains WHERE chain_code = 'CH01'").fetchone()[0],
            1,
        )

    def test_lookup_chain_by_chain_code_returns_expected_chain(self) -> None:
        created = self.chain_repository.upsert_chain(Chain(id=None, chain_code="CH01", name="Chain One"))

        found = self.chain_repository.get_by_chain_code("CH01")

        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.id, created.id)
        self.assertEqual(found.name, "Chain One")

    def test_lookup_missing_chain_code_returns_none(self) -> None:
        self.assertIsNone(self.chain_repository.get_by_chain_code("DOES_NOT_EXIST"))

    def test_insert_store(self) -> None:
        chain = self.chain_repository.upsert_chain(Chain(id=None, chain_code="CH01", name="Chain One"))

        created = self.store_repository.upsert_store(
            Store(
                id=None,
                chain_id=chain.id,
                store_code="ST01",
                name="Store One",
                city="New York",
                address="1 Main St",
                is_active=True,
            )
        )

        self.assertIsNotNone(created.id)
        self.assertEqual(created.chain_id, chain.id)
        self.assertEqual(created.store_code, "ST01")

    def test_update_existing_store_through_upsert(self) -> None:
        chain = self.chain_repository.upsert_chain(Chain(id=None, chain_code="CH01", name="Chain One"))
        self.store_repository.upsert_store(
            Store(
                id=None,
                chain_id=chain.id,
                store_code="ST01",
                name="Store One",
                city="New York",
                address="1 Main St",
                is_active=True,
            )
        )

        updated = self.store_repository.upsert_store(
            Store(
                id=None,
                chain_id=chain.id,
                store_code="ST01",
                name="Store One Updated",
                city="Boston",
                address="2 Main St",
                is_active=False,
            )
        )

        self.assertEqual(updated.name, "Store One Updated")
        self.assertEqual(updated.city, "Boston")
        self.assertFalse(updated.is_active)
        self.assertEqual(
            self.connection.execute(
                "SELECT COUNT(*) FROM stores WHERE chain_id = ? AND store_code = ?",
                (chain.id, "ST01"),
            ).fetchone()[0],
            1,
        )

    def test_lookup_store_by_chain_and_store_code_returns_expected_store(self) -> None:
        chain = self.chain_repository.upsert_chain(Chain(id=None, chain_code="CH01", name="Chain One"))
        created = self.store_repository.upsert_store(
            Store(
                id=None,
                chain_id=chain.id,
                store_code="ST01",
                name="Store One",
                city="New York",
                address="1 Main St",
                is_active=True,
            )
        )

        found = self.store_repository.get_by_chain_and_store_code(chain.id, "ST01")

        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.id, created.id)
        self.assertEqual(found.name, "Store One")

    def test_lookup_missing_store_returns_none(self) -> None:
        chain = self.chain_repository.upsert_chain(Chain(id=None, chain_code="CH01", name="Chain One"))

        self.assertIsNone(self.store_repository.get_by_chain_and_store_code(chain.id, "MISSING"))

    def test_retrieval_of_stores_by_chain_returns_only_matching_stores(self) -> None:
        chain_one = self.chain_repository.upsert_chain(Chain(id=None, chain_code="CH01", name="Chain One"))
        chain_two = self.chain_repository.upsert_chain(Chain(id=None, chain_code="CH02", name="Chain Two"))

        self.store_repository.upsert_store(
            Store(
                id=None,
                chain_id=chain_one.id,
                store_code="ST01",
                name="Chain One - Store One",
                city="New York",
                address="1 Main St",
                is_active=True,
            )
        )
        self.store_repository.upsert_store(
            Store(
                id=None,
                chain_id=chain_one.id,
                store_code="ST02",
                name="Chain One - Store Two",
                city="New York",
                address="2 Main St",
                is_active=True,
            )
        )
        self.store_repository.upsert_store(
            Store(
                id=None,
                chain_id=chain_two.id,
                store_code="ST99",
                name="Chain Two - Store One",
                city="Chicago",
                address="9 State St",
                is_active=True,
            )
        )

        stores_for_chain_one = self.store_repository.get_by_chain(chain_one.id)

        self.assertEqual(len(stores_for_chain_one), 2)
        self.assertTrue(all(store.chain_id == chain_one.id for store in stores_for_chain_one))
        self.assertEqual([store.store_code for store in stores_for_chain_one], ["ST01", "ST02"])


if __name__ == "__main__":
    unittest.main()
