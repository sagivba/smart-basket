"""Unit tests for currently implemented basket engine result-building behavior."""

from __future__ import annotations

import unittest

from Modules.engine.basket_engine import BasketEngine
from Modules.models.results import (
    AvailabilityStatus,
    BasketComparisonResult,
    BasketLineResult,
    ChainComparisonResult,
    MatchStatus,
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

    def test_build_chain_result_normalizes_numeric_unit_price_and_keeps_optional_fields(self) -> None:
        result = self.engine.build_chain_result(
            chain_id=21,
            chain_name="Chain Numeric",
            basket_items=[
                {
                    "product_id": None,
                    "product_name": "Bananas",
                    "barcode": None,
                    "quantity": 4,
                    "unit_price": 2,
                }
            ],
        )

        self.assertEqual(result.total_price, 8.0)
        self.assertEqual(result.found_items_count, 1)
        self.assertEqual(result.missing_items_count, 0)
        self.assertEqual(result.missing_items, [])

        line = result.basket_lines[0]
        self.assertIsNone(line.product_id)
        self.assertEqual(line.product_name, "Bananas")
        self.assertIsNone(line.barcode)
        self.assertEqual(line.quantity, 4)
        self.assertEqual(line.unit_price, 2.0)
        self.assertEqual(line.line_price, 8.0)
        self.assertEqual(line.availability_status, AvailabilityStatus.FOUND)

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
        self.assertEqual(result.ranked_chains[0].total_price, 6.0)
        self.assertEqual(result.ranked_chains[1].total_price, 15.0)

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

    def test_build_comparison_result_builds_multiple_chain_states(self) -> None:
        result = self.engine.build_comparison_result(
            chain_results_input=[
                {
                    "chain_id": 1,
                    "chain_name": "Chain One",
                    "basket_items": [
                        {
                            "product_id": 10,
                            "product_name": "Milk",
                            "barcode": "111",
                            "quantity": 2,
                            "unit_price": 4.5,
                        },
                        {
                            "product_id": 20,
                            "product_name": "Bread",
                            "barcode": "222",
                            "quantity": 1,
                            "unit_price": None,
                        },
                    ],
                },
                {
                    "chain_id": 2,
                    "chain_name": "Chain Two",
                },
            ],
            unmatched_items=["unknown-1"],
        )

        first = result.ranked_chains[0]
        second = result.ranked_chains[1]

        self.assertEqual(first.total_price, 9.0)
        self.assertFalse(first.is_complete_basket)
        self.assertEqual(first.found_items_count, 1)
        self.assertEqual(first.missing_items_count, 1)
        self.assertEqual(first.missing_items, ["Bread"])
        self.assertEqual(first.basket_lines[0].availability_status, AvailabilityStatus.FOUND)
        self.assertEqual(first.basket_lines[1].availability_status, AvailabilityStatus.MISSING)

        self.assertEqual(second.total_price, 0.0)
        self.assertTrue(second.is_complete_basket)
        self.assertEqual(second.found_items_count, 0)
        self.assertEqual(second.missing_items_count, 0)
        self.assertEqual(second.basket_lines, [])
        self.assertEqual(second.missing_items, [])

        self.assertEqual(result.unmatched_items, ["unknown-1"])

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

    def test_build_chain_result_rejects_non_integer_quantity_string(self) -> None:
        with self.assertRaisesRegex(TypeError, "quantity must be an integer"):
            self.engine.build_chain_result(
                chain_id=1,
                chain_name="Chain X",
                basket_items=[
                    {
                        "product_name": "Milk",
                        "quantity": "two",
                        "unit_price": 5.0,
                    }
                ],
            )

    def test_build_chain_result_requires_product_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "basket_item.product_name is required"):
            self.engine.build_chain_result(
                chain_id=1,
                chain_name="Chain X",
                basket_items=[{"quantity": 1, "unit_price": 5.0}],
            )


class TestBasketEngineNameMatching(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = BasketEngine()

    def test_match_input_item_by_name_returns_single_match_for_unambiguous_hit(self) -> None:
        result = self.engine.match_input_item_by_name(
            name="  MILK 1L  ",
            quantity=2,
            products_by_normalized_name={
                "milk 1l": [{"id": 10, "name": "Milk 1L", "barcode": "111"}]
            },
        )

        self.assertEqual(result["input_type"], "name")
        self.assertEqual(result["input_value"], "milk 1l")
        self.assertEqual(result["quantity"], 2)
        self.assertEqual(result["match_status"], MatchStatus.MATCHED.value)
        self.assertEqual(result["product_id"], 10)
        self.assertEqual(result["product_name"], "Milk 1L")
        self.assertEqual(result["barcode"], "111")
        self.assertEqual(result["candidate_products"], [])

    def test_match_input_item_by_name_returns_ambiguous_with_candidates(self) -> None:
        result = self.engine.match_input_item_by_name(
            name="cola",
            quantity=1,
            products_by_normalized_name={
                "cola": [
                    {"id": 1, "name": "Cola 330ml", "barcode": "100"},
                    {"id": 2, "name": "Cola Zero 330ml", "barcode": "200"},
                ]
            },
        )

        self.assertEqual(result["match_status"], MatchStatus.AMBIGUOUS.value)
        self.assertIsNone(result["product_id"])
        self.assertIsNone(result["product_name"])
        self.assertIsNone(result["barcode"])
        self.assertEqual(
            result["candidate_products"],
            [
                {"id": 1, "name": "Cola 330ml", "barcode": "100"},
                {"id": 2, "name": "Cola Zero 330ml", "barcode": "200"},
            ],
        )

    def test_match_input_item_by_name_returns_unmatched_for_unknown_name(self) -> None:
        result = self.engine.match_input_item_by_name(
            name="unknown product",
            quantity=1,
            products_by_normalized_name={},
        )

        self.assertEqual(result["match_status"], MatchStatus.UNMATCHED.value)
        self.assertIsNone(result["product_id"])
        self.assertIsNone(result["product_name"])
        self.assertIsNone(result["barcode"])
        self.assertEqual(result["candidate_products"], [])

    def test_match_basket_items_by_name_collects_only_unmatched_inputs(self) -> None:
        result = self.engine.match_basket_items_by_name(
            basket_items=[
                {"input_value": "Milk 1L", "quantity": 1},
                {"input_value": "Cola", "quantity": 1},
                {"input_value": "Unknown", "quantity": 1},
            ],
            products=[
                {"id": 10, "name": "Milk 1L", "barcode": "111", "normalized_name": "milk 1l"},
                {"id": 20, "name": "Cola 330ml", "barcode": "222", "normalized_name": "cola"},
                {
                    "id": 21,
                    "name": "Cola Zero 330ml",
                    "barcode": "223",
                    "normalized_name": "cola",
                },
            ],
        )

        self.assertEqual(len(result["matched_items"]), 3)
        self.assertEqual(
            [item["match_status"] for item in result["matched_items"]],
            [
                MatchStatus.MATCHED.value,
                MatchStatus.AMBIGUOUS.value,
                MatchStatus.UNMATCHED.value,
            ],
        )
        self.assertEqual(result["unmatched_items"], ["unknown"])


if __name__ == "__main__":
    unittest.main()
