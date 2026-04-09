"""Basket comparison orchestration and ranking services for the engine layer."""

from __future__ import annotations

from typing import Iterable, Sequence

from Modules.models.entities import BasketItem
from Modules.models.results import BasketComparisonResult, ChainComparisonResult


class BasketCalculator:
    """Engine contract for calculating chain comparison results from basket items."""

    def calculate(self, basket_items: Sequence[BasketItem]) -> list[ChainComparisonResult]:
        """Calculate per-chain basket results for matched basket items."""
        raise NotImplementedError


class BasketComparisonService:
    """Orchestrates basket comparison flow and chain ranking for MVP rules."""

    def __init__(self, calculator: BasketCalculator) -> None:
        self._calculator = calculator

    def compare_basket(
        self,
        basket_items: Sequence[BasketItem],
        unmatched_items: Sequence[str] | None = None,
    ) -> BasketComparisonResult:
        """Compare basket across chains and return a structured ranked result."""
        chain_results = self._calculator.calculate(basket_items)
        ranked_chains = self.rank_chains(chain_results)

        return BasketComparisonResult(
            ranked_chains=ranked_chains,
            unmatched_items=list(unmatched_items or []),
        )

    def rank_chains(
        self,
        chain_results: Iterable[ChainComparisonResult],
    ) -> list[ChainComparisonResult]:
        """Rank chains with complete baskets first, then by total price ascending."""
        return sorted(
            chain_results,
            key=lambda result: (
                0 if result.is_complete_basket else 1,
                result.total_price,
                result.chain_id,
            ),
        )
