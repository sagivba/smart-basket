"""Unit tests for basket engine comparison and ranking flow."""

from __future__ import annotations

import unittest

from Modules.engine.basket_engine import BasketCalculator, BasketComparisonService
from Modules.models.entities import BasketItem
from Modules.models.results import ChainComparisonResult


class _FakeCalculator(BasketCalculator):
    def __init__(self, results: list[ChainComparisonResult]) -> None:
        self.results = results
        self.received_items: list[BasketItem] | None = None

    def calculate(self, basket_items: list[BasketItem]) -> list[ChainComparisonResult]:
        self.received_items = basket_items
        return self.results


class TestBasketComparisonService(unittest.TestCase):
    def _make_chain_result(
        self,
        *,
        chain_id: int,
        chain_name: str,
        total_price: float,
        is_complete_basket: bool,
        missing_items_count: int,
    ) -> ChainComparisonResult:
        return ChainComparisonResult(
            chain_id=chain_id,
            chain_name=chain_name,
            total_price=total_price,
            found_items_count=2 - missing_items_count,
            missing_items_count=missing_items_count,
            is_complete_basket=is_complete_basket,
            basket_lines=[],
            missing_items=[],
        )

    def _make_basket_item(self) -> BasketItem:
        return BasketItem(
            id=1,
            basket_id=200,
            product_id=10,
            input_value="7290012345678",
            input_type="barcode",
            quantity=2,
            match_status="matched",
        )

    def test_should_rank_complete_baskets_before_partial_baskets(self) -> None:
        partial = self._make_chain_result(
            chain_id=2,
            chain_name="Partial Chain",
            total_price=10.0,
            is_complete_basket=False,
            missing_items_count=1,
        )
        complete = self._make_chain_result(
            chain_id=1,
            chain_name="Complete Chain",
            total_price=20.0,
            is_complete_basket=True,
            missing_items_count=0,
        )
        service = BasketComparisonService(_FakeCalculator([]))

        ranked = service.rank_chains([partial, complete])

        self.assertEqual([chain.chain_id for chain in ranked], [1, 2])

    def test_should_rank_by_lower_total_price_within_same_completeness_group(self) -> None:
        more_expensive = self._make_chain_result(
            chain_id=1,
            chain_name="Chain A",
            total_price=25.0,
            is_complete_basket=True,
            missing_items_count=0,
        )
        cheaper = self._make_chain_result(
            chain_id=2,
            chain_name="Chain B",
            total_price=19.0,
            is_complete_basket=True,
            missing_items_count=0,
        )
        service = BasketComparisonService(_FakeCalculator([]))

        ranked = service.rank_chains([more_expensive, cheaper])

        self.assertEqual([chain.chain_id for chain in ranked], [2, 1])

    def test_compare_basket_returns_structured_ranked_result(self) -> None:
        chain_a = self._make_chain_result(
            chain_id=1,
            chain_name="Chain A",
            total_price=22.0,
            is_complete_basket=True,
            missing_items_count=0,
        )
        chain_b = self._make_chain_result(
            chain_id=2,
            chain_name="Chain B",
            total_price=18.0,
            is_complete_basket=True,
            missing_items_count=0,
        )
        basket_item = self._make_basket_item()
        calculator = _FakeCalculator([chain_a, chain_b])
        service = BasketComparisonService(calculator)

        result = service.compare_basket([basket_item], unmatched_items=["unknown item"])

        self.assertEqual(calculator.received_items, [basket_item])
        self.assertEqual([chain.chain_id for chain in result.ranked_chains], [2, 1])
        self.assertEqual(result.unmatched_items, ["unknown item"])

    def test_rank_chains_is_deterministic_when_completeness_and_price_are_equal(self) -> None:
        first = self._make_chain_result(
            chain_id=10,
            chain_name="Chain Z",
            total_price=15.0,
            is_complete_basket=True,
            missing_items_count=0,
        )
        second = self._make_chain_result(
            chain_id=5,
            chain_name="Chain Y",
            total_price=15.0,
            is_complete_basket=True,
            missing_items_count=0,
        )
        service = BasketComparisonService(_FakeCalculator([]))

        ranked_from_forward = service.rank_chains([first, second])
        ranked_from_reverse = service.rank_chains([second, first])

        self.assertEqual([chain.chain_id for chain in ranked_from_forward], [5, 10])
        self.assertEqual([chain.chain_id for chain in ranked_from_reverse], [5, 10])


if __name__ == "__main__":
    unittest.main()
