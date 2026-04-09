"""Unit tests for basket engine calculations."""

from __future__ import annotations

import unittest
from decimal import Decimal

from Modules.engine.basket_engine import BasketCalculator
from Modules.models.entities import BasketItem


class FakePriceRepository:
    """In-memory fake repository for basket engine unit tests."""

    def __init__(self, prices_by_chain: dict[int, dict[int, Decimal]]) -> None:
        self.prices_by_chain = prices_by_chain
        self.last_product_ids: list[int] = []

    def get_prices_for_products_by_chain(
        self, product_ids: list[int]
    ) -> dict[int, dict[int, Decimal]]:
        self.last_product_ids = list(product_ids)
        return {
            chain_id: {
                product_id: unit_price
                for product_id, unit_price in chain_prices.items()
                if product_id in set(product_ids)
            }
            for chain_id, chain_prices in self.prices_by_chain.items()
        }


class TestBasketCalculator(unittest.TestCase):
    def _make_item(
        self,
        *,
        product_id: int | None,
        quantity: int,
        match_status: str,
        input_value: str = "input",
        input_type: str = "name",
    ) -> BasketItem:
        return BasketItem(
            id=None,
            basket_id=1,
            product_id=product_id,
            input_value=input_value,
            input_type=input_type,
            quantity=quantity,
            match_status=match_status,
        )

    def test_valid_basket_calculation_uses_only_matched_products(self) -> None:
        fake_repository = FakePriceRepository(
            prices_by_chain={
                1: {101: Decimal("5.00"), 102: Decimal("3.50")},
                2: {101: Decimal("4.75")},
            }
        )
        calculator = BasketCalculator(fake_repository)
        basket_items = [
            self._make_item(product_id=101, quantity=2, match_status="matched"),
            self._make_item(product_id=102, quantity=1, match_status="matched"),
            self._make_item(product_id=None, quantity=4, match_status="unmatched"),
        ]

        result = calculator.calculate_for_matched_products(basket_items)

        self.assertEqual(set(fake_repository.last_product_ids), {101, 102})
        self.assertEqual(result[1].line_prices[101], Decimal("10.00"))
        self.assertEqual(result[1].line_prices[102], Decimal("3.50"))
        self.assertEqual(result[2].line_prices[101], Decimal("9.50"))
        self.assertNotIn(102, result[2].line_prices)

    def test_quantity_validation_failure_raises_value_error(self) -> None:
        fake_repository = FakePriceRepository(prices_by_chain={1: {101: Decimal("2.00")}})
        calculator = BasketCalculator(fake_repository)
        invalid_item = self._make_item(product_id=101, quantity=1, match_status="matched")
        invalid_item.quantity = 0

        with self.assertRaisesRegex(ValueError, "positive integer"):
            calculator.calculate_for_matched_products([invalid_item])

    def test_line_price_equals_unit_price_times_quantity(self) -> None:
        fake_repository = FakePriceRepository(prices_by_chain={1: {101: Decimal("2.35")}})
        calculator = BasketCalculator(fake_repository)

        result = calculator.calculate_for_matched_products(
            [self._make_item(product_id=101, quantity=3, match_status="matched")]
        )

        self.assertEqual(result[1].line_prices[101], Decimal("7.05"))

    def test_total_chain_cost_is_sum_of_found_line_prices(self) -> None:
        fake_repository = FakePriceRepository(
            prices_by_chain={1: {101: Decimal("2.00"), 102: Decimal("3.50")}}
        )
        calculator = BasketCalculator(fake_repository)

        result = calculator.calculate_for_matched_products(
            [
                self._make_item(product_id=101, quantity=2, match_status="matched"),
                self._make_item(product_id=102, quantity=1, match_status="matched"),
                self._make_item(product_id=103, quantity=5, match_status="matched"),
            ]
        )

        self.assertEqual(result[1].total_price, Decimal("7.50"))

    def test_found_item_count_reflects_products_with_available_price_data(self) -> None:
        fake_repository = FakePriceRepository(
            prices_by_chain={
                1: {101: Decimal("2.00")},
                2: {102: Decimal("3.00"), 103: Decimal("1.00")},
            }
        )
        calculator = BasketCalculator(fake_repository)

        result = calculator.calculate_for_matched_products(
            [
                self._make_item(product_id=101, quantity=1, match_status="matched"),
                self._make_item(product_id=102, quantity=1, match_status="matched"),
                self._make_item(product_id=103, quantity=1, match_status="matched"),
            ]
        )

        self.assertEqual(result[1].found_items_count, 1)
        self.assertEqual(result[2].found_items_count, 2)


if __name__ == "__main__":
    unittest.main()
