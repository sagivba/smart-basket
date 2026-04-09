"""Unit tests for barcode matching behavior in the basket engine."""

from __future__ import annotations

import unittest

from Modules.engine.basket_engine import BarcodeMatchItem, BarcodeMatchResult, BasketEngine
from Modules.models.entities import Product
from Modules.models.results import MatchStatus


class InMemoryProductLookupRepository:
    """Deterministic in-memory product lookup by barcode for tests."""

    def __init__(self, products_by_barcode: dict[str, Product]) -> None:
        self._products_by_barcode = products_by_barcode

    def get_by_barcode(self, barcode: str) -> Product | None:
        return self._products_by_barcode.get(barcode)


class TestBasketEngineBarcodeMatching(unittest.TestCase):
    def test_match_by_barcodes_matches_known_barcode(self) -> None:
        known_product = Product(
            id=101,
            barcode="7290012345678",
            name="Milk 1L",
            normalized_name="milk 1l",
            brand="DairyCo",
            unit_name="1L",
        )
        engine = BasketEngine(
            InMemoryProductLookupRepository({known_product.barcode: known_product})
        )

        result = engine.match_by_barcodes(["7290012345678"])

        self.assertEqual(len(result.matched_items), 1)
        self.assertEqual(result.unmatched_items, [])
        self.assertEqual(result.matched_items[0].product_id, 101)
        self.assertEqual(result.matched_items[0].product_name, "Milk 1L")
        self.assertEqual(result.matched_items[0].match_status, MatchStatus.MATCHED)

    def test_match_by_barcodes_returns_unmatched_for_unknown_barcode(self) -> None:
        engine = BasketEngine(InMemoryProductLookupRepository({}))

        result = engine.match_by_barcodes(["7290099999999"])

        self.assertEqual(result.matched_items, [])
        self.assertEqual(result.unmatched_items, ["7290099999999"])

    def test_match_by_barcodes_returns_consistent_result_structure(self) -> None:
        known_product = Product(
            id=201,
            barcode="7290011111111",
            name="Bread",
            normalized_name="bread",
            brand=None,
            unit_name=None,
        )
        engine = BasketEngine(
            InMemoryProductLookupRepository({known_product.barcode: known_product})
        )

        result = engine.match_by_barcodes(["7290011111111", "7290022222222"])

        self.assertIsInstance(result, BarcodeMatchResult)
        self.assertIsInstance(result.matched_items, list)
        self.assertIsInstance(result.unmatched_items, list)

        matched_item = result.matched_items[0]
        self.assertIsInstance(matched_item, BarcodeMatchItem)
        self.assertEqual(matched_item.input_barcode, "7290011111111")
        self.assertEqual(matched_item.product_barcode, "7290011111111")
        self.assertEqual(matched_item.product_name, "Bread")
        self.assertEqual(matched_item.match_status, MatchStatus.MATCHED)

        self.assertEqual(result.unmatched_items, ["7290022222222"])


if __name__ == "__main__":
    unittest.main()
