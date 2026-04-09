"""Unit tests for currently implemented basket engine result-building behavior."""

from __future__ import annotations

import unittest

from Modules.engine.basket_engine import BasketCalculator, BasketComparisonService, BasketEngine
from Modules.models.entities import BasketItem
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


class _StubChainRepository:
    def list_chains(self) -> list[dict[str, object]]:
        return [
            {"id": 30, "name": "Partial Cheap"},
            {"id": 10, "name": "Complete Mid"},
            {"id": 20, "name": "Complete Expensive"},
            {"id": 40, "name": "Partial Expensive"},
            {"id": 25, "name": "Complete Mid Alt"},
        ]


class _StubProductRepository:
    def get_products_by_ids(self, product_ids: list[int]) -> list[dict[str, object]]:
        lookup = {
            1: {"id": 1, "name": "Milk", "barcode": "111"},
            2: {"id": 2, "name": "Bread", "barcode": "222"},
        }
        return [lookup[product_id] for product_id in product_ids if product_id in lookup]


class _StubPriceRepository:
    def get_prices_for_products_by_chain(
        self, product_ids: list[int]
    ) -> list[dict[str, object]]:
        rows = [
            {"chain_id": 10, "product_id": 1, "price": 5.0},
            {"chain_id": 10, "product_id": 2, "price": 3.0},
            {"chain_id": 20, "product_id": 1, "price": 6.0},
            {"chain_id": 20, "product_id": 2, "price": 4.0},
            {"chain_id": 25, "product_id": 1, "price": 5.0},
            {"chain_id": 25, "product_id": 2, "price": 3.0},
            {"chain_id": 30, "product_id": 1, "price": 2.0},
            {"chain_id": 40, "product_id": 1, "price": 7.0},
        ]
        return [row for row in rows if int(row["product_id"]) in product_ids]


class TestBasketComparisonService(unittest.TestCase):
    def setUp(self) -> None:
        self.service = BasketComparisonService(
            chain_repository=_StubChainRepository(),
            product_repository=_StubProductRepository(),
            price_repository=_StubPriceRepository(),
            calculator=BasketCalculator(engine=BasketEngine()),
        )

    def test_compare_basket_ranks_complete_before_partial_then_by_total_price(self) -> None:
        result = self.service.compare_basket(
            [
                BasketItem(
                    id=1,
                    basket_id=100,
                    product_id=1,
                    input_value="111",
                    input_type="barcode",
                    quantity=1,
                    match_status="matched",
                ),
                BasketItem(
                    id=2,
                    basket_id=100,
                    product_id=2,
                    input_value="222",
                    input_type="barcode",
                    quantity=1,
                    match_status="matched",
                ),
                BasketItem(
                    id=3,
                    basket_id=100,
                    product_id=None,
                    input_value="999",
                    input_type="barcode",
                    quantity=1,
                    match_status="unmatched",
                ),
            ]
        )

        self.assertIsInstance(result, BasketComparisonResult)
        self.assertEqual(
            [chain.chain_id for chain in result.ranked_chains],
            [10, 25, 20, 30, 40],
        )
        self.assertEqual([chain.total_price for chain in result.ranked_chains], [8.0, 8.0, 10.0, 2.0, 7.0])
        self.assertTrue(result.ranked_chains[0].is_complete_basket)
        self.assertTrue(result.ranked_chains[1].is_complete_basket)
        self.assertFalse(result.ranked_chains[3].is_complete_basket)
        self.assertEqual(result.ranked_chains[3].missing_items, ["Bread"])
        self.assertEqual(result.unmatched_items, ["999"])

    def test_compare_basket_keeps_unmatched_separate_from_missing_chain_items(self) -> None:
        result = self.service.compare_basket(
            [
                BasketItem(
                    id=1,
                    basket_id=200,
                    product_id=1,
                    input_value="111",
                    input_type="barcode",
                    quantity=2,
                    match_status="matched",
                ),
                BasketItem(
                    id=2,
                    basket_id=200,
                    product_id=999,
                    input_value="ghost",
                    input_type="name",
                    quantity=1,
                    match_status="matched",
                ),
            ]
        )

        self.assertEqual(result.unmatched_items, ["ghost"])
        first_chain = result.ranked_chains[0]
        self.assertEqual([line.product_name for line in first_chain.basket_lines], ["Milk"])
        self.assertNotIn("ghost", first_chain.missing_items)
        self.assertEqual(first_chain.found_items_count + first_chain.missing_items_count, 1)

    def test_rank_chains_uses_deterministic_chain_id_tie_breaker(self) -> None:
        complete_results = [
            BasketCalculator(engine=BasketEngine()).calculate_chain(
                chain={"id": 9, "name": "Z"},
                matched_items=[{"product_id": 1, "product_name": "Milk", "barcode": "111", "quantity": 1}],
                unit_prices_by_product_id={1: 5.0},
            ),
            BasketCalculator(engine=BasketEngine()).calculate_chain(
                chain={"id": 4, "name": "A"},
                matched_items=[{"product_id": 1, "product_name": "Milk", "barcode": "111", "quantity": 1}],
                unit_prices_by_product_id={1: 5.0},
            ),
        ]

        ranked = self.service.rank_chains(complete_results)
        self.assertEqual([chain.chain_id for chain in ranked], [4, 9])


if __name__ == "__main__":
    unittest.main()
