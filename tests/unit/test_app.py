"""Unit tests for application-layer orchestration."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from Modules.app.application_service import (
    AddBasketItemUseCase,
    ApplicationService,
    CompareBasketUseCase,
    ListChainsUseCase,
    LoadPricesUseCase,
)
from Modules.models.entities import BasketItem
from Modules.models.results import BasketComparisonResult


class TestLoadPricesUseCase(unittest.TestCase):
    def test_execute_delegates_to_loader(self) -> None:
        loader = Mock()
        load_request = {"prices_file": "data/samples/prices.csv", "mode": "append"}
        expected = {"loaded": 12, "rejected": 1}
        loader.load_prices.return_value = expected

        use_case = LoadPricesUseCase(loader=loader)

        result = use_case.execute(load_request)

        loader.load_prices.assert_called_once_with(load_request)
        self.assertEqual(result, expected)


class TestAddBasketItemUseCase(unittest.TestCase):
    def test_execute_delegates_to_basket_repository(self) -> None:
        repository = Mock()
        item = BasketItem(
            id=None,
            basket_id=11,
            product_id=55,
            input_value="7290012345678",
            input_type="barcode",
            quantity=2,
            match_status="matched",
        )
        saved_item = BasketItem(
            id=1,
            basket_id=11,
            product_id=55,
            input_value="7290012345678",
            input_type="barcode",
            quantity=2,
            match_status="matched",
        )
        repository.add_item.return_value = saved_item

        use_case = AddBasketItemUseCase(basket_repository=repository)

        result = use_case.execute(item)

        repository.add_item.assert_called_once_with(item)
        self.assertEqual(result, saved_item)


class TestCompareBasketUseCase(unittest.TestCase):
    def test_execute_loads_basket_items_then_compares(self) -> None:
        repository = Mock()
        comparison_service = Mock()
        basket_id = 77
        basket_items = [
            BasketItem(
                id=10,
                basket_id=basket_id,
                product_id=1001,
                input_value="milk",
                input_type="name",
                quantity=1,
                match_status="matched",
            )
        ]
        comparison_result = BasketComparisonResult(ranked_chains=[], unmatched_items=[])
        repository.get_by_basket_id.return_value = basket_items
        comparison_service.compare_basket.return_value = comparison_result

        use_case = CompareBasketUseCase(
            basket_repository=repository,
            comparison_service=comparison_service,
        )

        result = use_case.execute(basket_id)

        repository.get_by_basket_id.assert_called_once_with(basket_id)
        comparison_service.compare_basket.assert_called_once_with(basket_items)
        self.assertEqual(result, comparison_result)


class TestListChainsUseCase(unittest.TestCase):
    def test_execute_delegates_to_chain_repository(self) -> None:
        chain_repository = Mock()
        chains = [{"id": 1, "name": "Chain A"}, {"id": 2, "name": "Chain B"}]
        chain_repository.list_chains.return_value = chains

        use_case = ListChainsUseCase(chain_repository=chain_repository)

        result = use_case.execute()

        chain_repository.list_chains.assert_called_once_with()
        self.assertEqual(result, chains)


class TestApplicationService(unittest.TestCase):
    def test_facade_methods_delegate_to_corresponding_use_cases(self) -> None:
        load_prices_use_case = Mock()
        add_basket_item_use_case = Mock()
        compare_basket_use_case = Mock()
        list_chains_use_case = Mock()

        service = ApplicationService(
            load_prices_use_case=load_prices_use_case,
            add_basket_item_use_case=add_basket_item_use_case,
            compare_basket_use_case=compare_basket_use_case,
            list_chains_use_case=list_chains_use_case,
        )

        load_request = {"prices_file": "data/samples/prices.csv"}
        input_item = BasketItem(
            id=None,
            basket_id=88,
            product_id=None,
            input_value="bread",
            input_type="name",
            quantity=1,
            match_status="unmatched",
        )

        saved_item = BasketItem(
            id=42,
            basket_id=88,
            product_id=None,
            input_value="bread",
            input_type="name",
            quantity=1,
            match_status="unmatched",
        )
        compare_result = BasketComparisonResult(ranked_chains=[], unmatched_items=["bread"])
        chains_result = ["Chain A", "Chain B"]

        load_prices_use_case.execute.return_value = {"accepted": 3}
        add_basket_item_use_case.execute.return_value = saved_item
        compare_basket_use_case.execute.return_value = compare_result
        list_chains_use_case.execute.return_value = chains_result

        self.assertEqual(service.load_prices(load_request), {"accepted": 3})
        self.assertEqual(service.add_basket_item(input_item), saved_item)
        self.assertEqual(service.compare_basket(88), compare_result)
        self.assertEqual(service.list_chains(), chains_result)

        load_prices_use_case.execute.assert_called_once_with(load_request)
        add_basket_item_use_case.execute.assert_called_once_with(input_item)
        compare_basket_use_case.execute.assert_called_once_with(88)
        list_chains_use_case.execute.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
