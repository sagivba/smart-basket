"""Basket calculation engine for matched products."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable, Protocol

from Modules.models.entities import BasketItem


class PriceRepositoryProtocol(Protocol):
    """Protocol for the price lookup dependency used by the basket calculator."""

    def get_prices_for_products_by_chain(
        self, product_ids: list[int]
    ) -> dict[int, dict[int, Decimal]]:
        """Return prices by chain and product identifier."""


@dataclass(slots=True)
class ChainCostSummary:
    """Calculated basket cost summary for a single chain."""

    chain_id: int
    line_prices: dict[int, Decimal] = field(default_factory=dict)
    total_price: Decimal = Decimal("0")
    found_items_count: int = 0


class BasketCalculator:
    """Calculates matched-item basket costs across chains."""

    def __init__(self, price_repository: PriceRepositoryProtocol) -> None:
        self._price_repository = price_repository

    def calculate_for_matched_products(
        self, basket_items: Iterable[BasketItem]
    ) -> dict[int, ChainCostSummary]:
        """Validate items and calculate chain costs for matched products only."""
        items = list(basket_items)
        self._validate_basket_items(items)

        matched_quantities = self._collect_matched_product_quantities(items)
        if not matched_quantities:
            return {}

        product_ids = list(matched_quantities)
        prices_by_chain = self._price_repository.get_prices_for_products_by_chain(product_ids)

        return self._calculate_chain_costs(matched_quantities, prices_by_chain)

    @staticmethod
    def _validate_basket_items(basket_items: Iterable[BasketItem]) -> None:
        for item in basket_items:
            if not isinstance(item.quantity, int) or item.quantity <= 0:
                raise ValueError("quantity must be a positive integer")

    @staticmethod
    def _collect_matched_product_quantities(
        basket_items: Iterable[BasketItem],
    ) -> dict[int, int]:
        matched_quantities: dict[int, int] = {}
        for item in basket_items:
            if item.match_status != "matched" or item.product_id is None:
                continue

            matched_quantities[item.product_id] = (
                matched_quantities.get(item.product_id, 0) + item.quantity
            )

        return matched_quantities

    @staticmethod
    def _calculate_chain_costs(
        matched_quantities: dict[int, int],
        prices_by_chain: dict[int, dict[int, Decimal]],
    ) -> dict[int, ChainCostSummary]:
        chain_summaries: dict[int, ChainCostSummary] = {}

        for chain_id, chain_product_prices in prices_by_chain.items():
            summary = ChainCostSummary(chain_id=chain_id)

            for product_id, quantity in matched_quantities.items():
                unit_price = chain_product_prices.get(product_id)
                if unit_price is None:
                    continue

                line_price = unit_price * quantity
                summary.line_prices[product_id] = line_price
                summary.total_price += line_price
                summary.found_items_count += 1

            chain_summaries[chain_id] = summary

        return chain_summaries
