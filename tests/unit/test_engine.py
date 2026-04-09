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

    def test_build_chain_result_builds_found_and_missing_lines_with_expected_totals(self) -> None:
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

        self.assertIsInstance(result, ChainComparisonResult)
        self.assertEqual(result.chain_id, 11)
        self.assertEqual(result.chain_name, "Chain B")
        self.assertEqual(result.total_price, 9.0)
        self.assertEqual(result.found_items_count, 1)
        self.assertEqual(result.missing_items_count, 1)
        self.assertFalse(result.is_complete_basket)
        self.assertEqual(result.missing_items, ["Bread"])

        found_line = result.basket_lines[0]
        missing_line = result.basket_lines[1]

        self.assertEqual(found_line.product_id, 1)
        self.assertEqual(found_line.product_name, "Milk")
        self.assertEqual(found_line.barcode, "111")
        self.assertEqual(found_line.quantity, 2)
        self.assertEqual(found_line.unit_price, 4.5)
        self.assertEqual(found_line.line_price, 9.0)
        self.assertEqual(found_line.availability_status, AvailabilityStatus.FOUND)

        self.assertEqual(missing_line.product_id, 2)
        self.assertEqual(missing_line.product_name, "Bread")
        self.assertEqual(missing_line.barcode, "222")
        self.assertEqual(missing_line.quantity, 1)
        self.assertIsNone(missing_line.unit_price)
        self.assertIsNone(missing_line.line_price)
        self.assertEqual(missing_line.availability_status, AvailabilityStatus.MISSING)

    def test_build_chain_result_marks_complete_when_no_missing_items(self) -> None:
        result = self.engine.build_chain_result(
            chain_id=12,
            chain_name="Chain C",
            basket_items=[
                {
                    "product_id": 7,
                    "product_name": "Eggs",
                    "barcode": "333",
                    "quantity": 3,
                    "unit_price": 12.0,
                }
            ],
        )

        self.assertTrue(result.is_complete_basket)
        self.assertEqual(result.missing_items_count, 0)
        self.assertEqual(result.found_items_count, 1)
        self.assertEqual(result.total_price, 36.0)

    def test_build_chain_result_handles_empty_basket_items(self) -> None:
        result = self.engine.build_chain_result(
            chain_id=99,
            chain_name="Empty Chain",
            basket_items=[],
        )

        self.assertEqual(result.total_price, 0.0)
        self.assertEqual(result.found_items_count, 0)
        self.assertEqual(result.missing_items_count, 0)
        self.assertTrue(result.is_complete_basket)
        self.assertEqual(result.basket_lines, [])
        self.assertEqual(result.missing_items, [])

    def test_build_comparison_result_preserves_chain_order_and_model_types(self) -> None:
        result = self.engine.build_comparison_result(
            chain_results_input=[
                {
                    "chain_id": "20",
                    "chain_name": "42",
                    "basket_items": [
                        {
                            "product_id": 101,
                            "product_name": "Pasta",
                            "barcode": "444",
                            "quantity": 1,
                            "unit_price": 6.0,
                        }
                    ],
                },
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
                },
            ],
        )

        self.assertIsInstance(result, BasketComparisonResult)
        self.assertEqual(len(result.ranked_chains), 2)
        self.assertIsInstance(result.ranked_chains[0], ChainComparisonResult)
        self.assertIsInstance(result.ranked_chains[0].basket_lines[0], BasketLineResult)
        self.assertEqual(result.ranked_chains[0].chain_id, 20)
        self.assertEqual(result.ranked_chains[0].chain_name, "42")
        self.assertEqual(result.ranked_chains[1].chain_id, 30)
        self.assertEqual(result.ranked_chains[1].chain_name, "Chain E")

    def test_build_comparison_result_returns_copy_of_unmatched_items(self) -> None:
        unmatched = ["unknown barcode 999", "mystery item"]
        result = self.engine.build_comparison_result(
            chain_results_input=[],
            unmatched_items=unmatched,
        )

        self.assertEqual(result.unmatched_items, unmatched)
        self.assertIsNot(result.unmatched_items, unmatched)

    def test_build_comparison_result_defaults_unmatched_items_to_empty_list(self) -> None:
        result = self.engine.build_comparison_result(chain_results_input=[])

        self.assertEqual(result.unmatched_items, [])

    def test_build_chain_result_rejects_non_numeric_unit_price(self) -> None:
        with self.assertRaises(TypeError):
            self.engine.build_chain_result(
                chain_id=1,
                chain_name="Chain X",
                basket_items=[
                    {
                        "product_name": "Milk",
                        "quantity": 1,
                        "unit_price": "5.0",
                    }
                ],
            )

    def test_build_chain_result_rejects_boolean_unit_price(self) -> None:
        with self.assertRaises(TypeError):
            self.engine.build_chain_result(
                chain_id=1,
                chain_name="Chain X",
                basket_items=[
                    {
                        "product_name": "Milk",
                        "quantity": 1,
                        "unit_price": True,
                    }
                ],
            )

    def test_build_chain_result_rejects_negative_unit_price(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.build_chain_result(
                chain_id=1,
                chain_name="Chain X",
                basket_items=[
                    {
                        "product_name": "Milk",
                        "quantity": 1,
                        "unit_price": -0.01,
                    }
                ],
            )

    def test_build_chain_result_rejects_non_positive_quantity(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.build_chain_result(
                chain_id=1,
                chain_name="Chain X",
                basket_items=[
                    {
                        "product_name": "Milk",
                        "quantity": 0,
                        "unit_price": 5.0,
                    }
                ],
            )


class TestBasketEngineBarcodeMatching(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = BasketEngine()

    def test_match_input_item_by_barcode_returns_direct_product_match(self) -> None:
        result = self.engine.match_input_item_by_barcode(
            barcode=" 7290012345678 ",
            quantity=2,
            products_by_barcode={
                "7290012345678": {
                    "id": 101,
                    "barcode": "7290012345678",
                    "name": "Milk 1L",
                }
            },
        )

        self.assertEqual(result["input_type"], "barcode")
        self.assertEqual(result["input_value"], "7290012345678")
        self.assertEqual(result["quantity"], 2)
        self.assertEqual(result["match_status"], "matched")
        self.assertEqual(result["product_id"], 101)
        self.assertEqual(result["product_name"], "Milk 1L")
        self.assertEqual(result["barcode"], "7290012345678")

    def test_match_input_item_by_barcode_marks_unknown_barcode_as_unmatched(self) -> None:
        result = self.engine.match_input_item_by_barcode(
            barcode="0000000000000",
            quantity=1,
            products_by_barcode={},
        )

        self.assertEqual(result["match_status"], "unmatched")
        self.assertIsNone(result["product_id"])
        self.assertIsNone(result["product_name"])
        self.assertEqual(result["barcode"], "0000000000000")

    def test_match_basket_items_by_barcode_returns_consistent_structure(self) -> None:
        match_output = self.engine.match_basket_items_by_barcode(
            basket_items=[
                {"input_value": "111", "quantity": 1},
                {"input_value": "999", "quantity": 2},
            ],
            products=[
                {"id": 1, "barcode": "111", "name": "Bread"},
                {"id": 2, "barcode": "222", "name": "Milk"},
            ],
        )

        self.assertEqual(match_output["unmatched_items"], ["999"])
        self.assertEqual(len(match_output["matched_items"]), 2)

        first_keys = set(match_output["matched_items"][0].keys())
        second_keys = set(match_output["matched_items"][1].keys())
        self.assertEqual(first_keys, second_keys)
        self.assertEqual(
            first_keys,
            {
                "input_type",
                "input_value",
                "quantity",
                "match_status",
                "product_id",
                "product_name",
                "barcode",
            },
        )

if __name__ == "__main__":
    unittest.main()
