"""Unit tests for core domain entities."""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from Modules.models.entities import BasketItem, Chain, Price, Product, Store
from Modules.models.results import (
    AVAILABILITY_STATUS_FOUND,
    AVAILABILITY_STATUS_MISSING,
    MATCH_STATUS_AMBIGUOUS,
    MATCH_STATUS_MATCHED,
    MATCH_STATUS_UNMATCHED,
    AvailabilityStatus,
    MatchStatus,
)


class TestCoreDomainEntities(unittest.TestCase):
    def test_product_valid_construction_and_trimming(self) -> None:
        product = Product(
            id=1,
            barcode=" 7290012345678 ",
            name="  Milk  ",
            normalized_name=" milk ",
            brand="  DairyCo ",
            unit_name=" 1L ",
        )

        self.assertEqual(product.barcode, "7290012345678")
        self.assertEqual(product.name, "Milk")
        self.assertEqual(product.normalized_name, "milk")
        self.assertEqual(product.brand, "DairyCo")
        self.assertEqual(product.unit_name, "1L")

    def test_chain_valid_construction(self) -> None:
        chain = Chain(id=1, chain_code=" CH01 ", name="  Best Chain ")

        self.assertEqual(chain.chain_code, "CH01")
        self.assertEqual(chain.name, "Best Chain")

    def test_store_valid_construction(self) -> None:
        store = Store(
            id=1,
            chain_id=1,
            store_code=" S001 ",
            name="  Main Branch ",
            city="  New York ",
            address=" 123 Main St ",
            is_active=True,
        )

        self.assertEqual(store.store_code, "S001")
        self.assertEqual(store.name, "Main Branch")
        self.assertEqual(store.city, "New York")
        self.assertEqual(store.address, "123 Main St")
        self.assertTrue(store.is_active)

    def test_price_valid_construction_and_trimming(self) -> None:
        price = Price(
            id=1,
            product_id=10,
            chain_id=5,
            store_id=8,
            price=" 14.90 ",
            currency=" ILS ",
            price_date=date(2026, 4, 9),
            source_file=" prices.csv ",
        )

        self.assertEqual(price.price, Decimal("14.90"))
        self.assertEqual(price.currency, "ILS")
        self.assertEqual(price.source_file, "prices.csv")

    def test_price_rejects_negative_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be negative"):
            Price(
                id=1,
                product_id=10,
                chain_id=5,
                store_id=8,
                price="-0.01",
                currency="USD",
                price_date=date(2026, 4, 9),
                source_file=None,
            )

    def test_basket_item_valid_construction_and_trimming(self) -> None:
        basket_item = BasketItem(
            id=1,
            basket_id=33,
            product_id=10,
            input_value=" 7290012345678 ",
            input_type=" barcode ",
            quantity=2,
            match_status=" matched ",
        )

        self.assertEqual(basket_item.input_value, "7290012345678")
        self.assertEqual(basket_item.input_type, "barcode")
        self.assertEqual(basket_item.match_status, "matched")
        self.assertEqual(basket_item.quantity, 2)
        self.assertEqual(basket_item.candidate_product_ids, [])

    def test_basket_item_preserves_candidate_product_ids(self) -> None:
        basket_item = BasketItem(
            id=1,
            basket_id=33,
            product_id=None,
            input_value="milk",
            input_type="name",
            quantity=1,
            match_status="ambiguous",
            candidate_product_ids=[10, 12],
        )

        self.assertEqual(basket_item.candidate_product_ids, [10, 12])

    def test_basket_item_rejects_non_positive_quantity(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive integer"):
            BasketItem(
                id=1,
                basket_id=33,
                product_id=10,
                input_value="7290012345678",
                input_type="barcode",
                quantity=0,
                match_status="matched",
            )

    def test_basket_item_rejects_non_integer_quantity(self) -> None:
        with self.assertRaisesRegex(TypeError, "integer"):
            BasketItem(
                id=1,
                basket_id=33,
                product_id=10,
                input_value="milk",
                input_type="name",
                quantity=1.5,
                match_status="matched",
            )


class TestResultModelSharedConstants(unittest.TestCase):
    def test_match_status_enum_values_use_shared_constants(self) -> None:
        self.assertEqual(MatchStatus.MATCHED.value, MATCH_STATUS_MATCHED)
        self.assertEqual(MatchStatus.UNMATCHED.value, MATCH_STATUS_UNMATCHED)
        self.assertEqual(MatchStatus.AMBIGUOUS.value, MATCH_STATUS_AMBIGUOUS)

    def test_availability_status_enum_values_use_shared_constants(self) -> None:
        self.assertEqual(AvailabilityStatus.FOUND.value, AVAILABILITY_STATUS_FOUND)
        self.assertEqual(AvailabilityStatus.MISSING.value, AVAILABILITY_STATUS_MISSING)


if __name__ == "__main__":
    unittest.main()
