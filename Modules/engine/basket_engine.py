"""Basket comparison result building logic for the engine layer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from numbers import Real
from typing import Any

from Modules.models.results import (
    AvailabilityStatus,
    BasketComparisonResult,
    BasketLineResult,
    ChainComparisonResult,
)


class BasketEngine:
    """Builds structured basket comparison results for chains."""

    def build_chain_result(
        self,
        *,
        chain_id: int,
        chain_name: str,
        basket_items: Sequence[Mapping[str, Any]],
    ) -> ChainComparisonResult:
        """Build a single chain comparison result from matched basket items."""
        validated_basket_items = self._validate_basket_items_for_calculation(basket_items)
        self.collect_matched_product_ids(validated_basket_items)

        basket_lines: list[BasketLineResult] = []
        missing_items: list[str] = []
        total_price = 0.0

        for basket_item in validated_basket_items:
            line_result = self._build_line_result(basket_item)
            basket_lines.append(line_result)

            if line_result.availability_status is AvailabilityStatus.MISSING:
                missing_items.append(line_result.product_name)
                continue

            if line_result.line_price is not None:
                total_price += line_result.line_price

        missing_items_count = len(missing_items)
        found_items_count = len(basket_lines) - missing_items_count

        return ChainComparisonResult(
            chain_id=chain_id,
            chain_name=chain_name,
            total_price=total_price,
            found_items_count=found_items_count,
            missing_items_count=missing_items_count,
            is_complete_basket=missing_items_count == 0,
            basket_lines=basket_lines,
            missing_items=missing_items,
        )

    def build_comparison_result(
        self,
        *,
        chain_results_input: Sequence[Mapping[str, Any]],
        unmatched_items: Sequence[str] | None = None,
    ) -> BasketComparisonResult:
        """Build top-level comparison result while preserving chain input order."""
        ranked_chains = [
            self.build_chain_result(
                chain_id=int(chain_input["chain_id"]),
                chain_name=str(chain_input["chain_name"]),
                basket_items=chain_input.get("basket_items", []),
            )
            for chain_input in chain_results_input
        ]

        return BasketComparisonResult(
            ranked_chains=ranked_chains,
            unmatched_items=list(unmatched_items or []),
        )

    def collect_matched_product_ids(
        self, basket_items: Sequence[Mapping[str, Any]]
    ) -> list[int]:
        """Collect unique matched product IDs from basket items, preserving order."""
        matched_product_ids: list[int] = []
        seen_product_ids: set[int] = set()

        for basket_item in basket_items:
            product_id = basket_item.get("product_id")
            if product_id is None:
                continue

            if not isinstance(product_id, int) or isinstance(product_id, bool):
                raise TypeError("product_id must be an integer when provided")

            if product_id not in seen_product_ids:
                seen_product_ids.add(product_id)
                matched_product_ids.append(product_id)

        return matched_product_ids

    def _validate_basket_items_for_calculation(
        self, basket_items: Sequence[Mapping[str, Any]]
    ) -> list[Mapping[str, Any]]:
        """Validate all items required for line and total-price calculation."""
        return [self._validate_basket_item_for_calculation(item) for item in basket_items]

    def _validate_basket_item_for_calculation(
        self, basket_item: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """Validate a single basket item used for calculation."""
        if "quantity" not in basket_item:
            raise ValueError("basket_item.quantity is required")
        if "product_name" not in basket_item:
            raise ValueError("basket_item.product_name is required")

        quantity = basket_item["quantity"]
        if not isinstance(quantity, int) or isinstance(quantity, bool):
            raise TypeError("quantity must be an integer")
        if quantity <= 0:
            raise ValueError("quantity must be a positive integer")

        product_name = basket_item["product_name"]
        if not isinstance(product_name, str):
            raise TypeError("product_name must be a string")
        if not product_name.strip():
            raise ValueError("product_name must not be empty")

        self._normalize_unit_price(basket_item.get("unit_price"))
        return basket_item

    def _build_line_result(self, basket_item: Mapping[str, Any]) -> BasketLineResult:
        """Build a line result and mark availability from the given unit price."""
        unit_price = self._normalize_unit_price(basket_item.get("unit_price"))
        quantity = int(basket_item["quantity"])

        availability_status = (
            AvailabilityStatus.MISSING
            if unit_price is None
            else AvailabilityStatus.FOUND
        )

        line_price = None if unit_price is None else unit_price * quantity

        return BasketLineResult(
            product_id=basket_item.get("product_id"),
            product_name=str(basket_item["product_name"]),
            barcode=basket_item.get("barcode"),
            quantity=quantity,
            unit_price=unit_price,
            line_price=line_price,
            availability_status=availability_status,
        )

    def _normalize_unit_price(self, unit_price: Any) -> float | None:
        """Normalize unit price into a float or None when missing."""
        if unit_price is None:
            return None

        if isinstance(unit_price, bool) or not isinstance(unit_price, Real):
            raise TypeError("unit_price must be numeric or None")

        normalized_unit_price = float(unit_price)
        if normalized_unit_price < 0:
            raise ValueError("unit_price must not be negative")

        return normalized_unit_price
