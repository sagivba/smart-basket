"""Unit tests for basket engine result-building behavior."""

from __future__ import annotations

import unittest

from Modules.engine.basket_engine import BasketEngine
from Modules.models.results import (
    AvailabilityStatus,
    BasketComparisonResult,
    BasketLineResult,
    ChainComparisonResult,
)


class TestBasketEngineResultBuilding(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = BasketEngine()

    def test_build_chain_result_marks_missing_product(self) -> None:
        result = self.engine.build_chain_result(
            chain_id=10,
            chain_name="Chain A",
            basket_items=[
                {
                    "product_id": 1001,
                    "product_name": "Milk",
                    "barcode": "729001",
                    "quantity": 2,
                    "unit_price": None,
                }
            ],
        )

        self.assertEqual(result.missing_items, ["Milk"])
        self.assertEqual(result.missing_items_count, 1)
        self.assertEqual(result.found_items_count, 0)
        self.assertFalse(result.is_complete_basket)
        self.assertEqual(result.basket_lines[0].availability_status, AvailabilityStatus.MISSING)

    def test_build_chain_result_collects_missing_items_and_totals(self) -> None:
        result = self.engine.build_chain_result(
            chain_id=11,
            chain_name="Chain B",
            basket_items=[
                {
                    "product_id": 1,
                    "product_name": "Milk",
                    "barcode": "111",
                    "quantity": 2,
                    "unit_price": 4.5,
                },
                {
                    "product_id": 2,
                    "product_name": "Bread",
                    "barcode": "222",
                    "quantity": 1,
                    "unit_price": None,
                },
            ],
        )

        self.assertEqual(result.missing_items, ["Bread"])
        self.assertEqual(result.missing_items_count, 1)
        self.assertEqual(result.found_items_count, 1)
        self.assertEqual(result.total_price, 9.0)

    def test_is_complete_basket_true_when_no_missing_items(self) -> None:
        result = self.engine.build_chain_result(
            chain_id=12,
            chain_name="Chain C",
            basket_items=[
                {
                    "product_id": 7,
                    "product_name": "Eggs",
                    "barcode": "333",
                    "quantity": 1,
                    "unit_price": 12.0,
                }
            ],
        )

        self.assertTrue(result.is_complete_basket)
        self.assertEqual(result.missing_items_count, 0)

    def test_build_comparison_result_returns_unmatched_separately(self) -> None:
        result = self.engine.build_comparison_result(
            chain_results_input=[
                {
                    "chain_id": 20,
                    "chain_name": "Chain D",
                    "basket_items": [
                        {
                            "product_id": 101,
                            "product_name": "Pasta",
                            "barcode": "444",
                            "quantity": 1,
                            "unit_price": 6.0,
                        }
                    ],
                }
            ],
            unmatched_items=["unknown barcode 999", "mystery item"],
        )

        self.assertEqual(result.unmatched_items, ["unknown barcode 999", "mystery item"])
        self.assertEqual(len(result.ranked_chains), 1)
        self.assertEqual(result.ranked_chains[0].chain_name, "Chain D")

    def test_builds_structured_result_models(self) -> None:
        result = self.engine.build_comparison_result(
            chain_results_input=[
                {
                    "chain_id": 30,
                    "chain_name": "Chain E",
                    "basket_items": [
                        {
                            "product_id": 501,
                            "product_name": "Rice",
                            "barcode": "555",
                            "quantity": 3,
                            "unit_price": 5.0,
                        }
                    ],
                }
            ],
            unmatched_items=[],
        )

        self.assertIsInstance(result, BasketComparisonResult)
        self.assertIsInstance(result.ranked_chains[0], ChainComparisonResult)
        self.assertIsInstance(result.ranked_chains[0].basket_lines[0], BasketLineResult)
        self.assertEqual(
            result.ranked_chains[0].basket_lines[0].availability_status,
            AvailabilityStatus.FOUND,
        )


if __name__ == "__main__":
    unittest.main()
