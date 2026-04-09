"""Integration tests for end-to-end basket comparison result building."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from Modules.engine.basket_engine import BasketEngine
from Modules.models.results import AvailabilityStatus, BasketComparisonResult


class TestBasketComparisonIntegration(unittest.TestCase):
    """Integration scenario for the currently implemented comparison flow."""

    def test_build_comparison_result_end_to_end_with_missing_and_unmatched_items(self) -> None:
        fixture_path = Path("tests/fixtures/integration/basket_comparison_case.json")
        fixture_payload = json.loads(fixture_path.read_text(encoding="utf-8"))

        engine = BasketEngine()
        result = engine.build_comparison_result(
            chain_results_input=fixture_payload["chain_results_input"],
            unmatched_items=fixture_payload["unmatched_items"],
        )

        self.assertIsInstance(result, BasketComparisonResult)
        self.assertEqual(result.unmatched_items, ["unknown barcode 999", "mystery snack"])
        self.assertEqual(len(result.ranked_chains), 2)

        budget_chain = result.ranked_chains[0]
        complete_chain = result.ranked_chains[1]

        self.assertEqual(budget_chain.chain_id, 101)
        self.assertEqual(budget_chain.chain_name, "Budget Chain")
        self.assertEqual(budget_chain.total_price, 17.5)
        self.assertEqual(budget_chain.found_items_count, 2)
        self.assertEqual(budget_chain.missing_items_count, 1)
        self.assertFalse(budget_chain.is_complete_basket)
        self.assertEqual(budget_chain.missing_items, ["Eggs 12"])

        budget_missing_line = budget_chain.basket_lines[2]
        self.assertEqual(budget_missing_line.product_name, "Eggs 12")
        self.assertEqual(budget_missing_line.availability_status, AvailabilityStatus.MISSING)
        self.assertIsNone(budget_missing_line.unit_price)
        self.assertIsNone(budget_missing_line.line_price)

        self.assertEqual(complete_chain.chain_id, 202)
        self.assertEqual(complete_chain.chain_name, "Complete Chain")
        self.assertEqual(complete_chain.total_price, 30.0)
        self.assertEqual(complete_chain.found_items_count, 3)
        self.assertEqual(complete_chain.missing_items_count, 0)
        self.assertTrue(complete_chain.is_complete_basket)
        self.assertEqual(complete_chain.missing_items, [])

        complete_chain_line_prices = [line.line_price for line in complete_chain.basket_lines]
        self.assertEqual(complete_chain_line_prices, [11.0, 7.0, 12.0])
        self.assertTrue(
            all(
                line.availability_status is AvailabilityStatus.FOUND
                for line in complete_chain.basket_lines
            )
        )


if __name__ == "__main__":
    unittest.main()
