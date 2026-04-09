"""Unit tests for application-layer orchestration."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from Modules.app.application_service import (
    AddBasketItemUseCase,
    ApplicationService,
    ClearBasketUseCase,
    CompareBasketUseCase,
    DownloadTransparencyFilesUseCase,
    GetBasketStateUseCase,
    ListChainsUseCase,
    LoadPricesUseCase,
    RemoveBasketItemUseCase,
    UpdateBasketItemQuantityUseCase,
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
        download_transparency_use_case = Mock()
        update_quantity_use_case = Mock()
        remove_basket_item_use_case = Mock()
        clear_basket_use_case = Mock()
        get_basket_state_use_case = Mock()

        service = ApplicationService(
            load_prices_use_case=load_prices_use_case,
            add_basket_item_use_case=add_basket_item_use_case,
            compare_basket_use_case=compare_basket_use_case,
            list_chains_use_case=list_chains_use_case,
            download_transparency_files_use_case=download_transparency_use_case,
            update_basket_item_quantity_use_case=update_quantity_use_case,
            remove_basket_item_use_case=remove_basket_item_use_case,
            clear_basket_use_case=clear_basket_use_case,
            get_basket_state_use_case=get_basket_state_use_case,
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
        updated_item = BasketItem(
            id=42,
            basket_id=88,
            product_id=None,
            input_value="bread",
            input_type="name",
            quantity=4,
            match_status="unmatched",
        )
        basket_state = {"basket_id": 88, "item_count": 1, "items": []}

        load_prices_use_case.execute.return_value = {"accepted": 3}
        add_basket_item_use_case.execute.return_value = saved_item
        compare_basket_use_case.execute.return_value = compare_result
        list_chains_use_case.execute.return_value = chains_result
        download_transparency_use_case.execute.return_value = {"success": True}
        update_quantity_use_case.execute.return_value = updated_item
        clear_basket_use_case.execute.return_value = 1
        get_basket_state_use_case.execute.return_value = basket_state

        self.assertEqual(service.load_prices(load_request), {"accepted": 3})
        self.assertEqual(service.add_basket_item(input_item), saved_item)
        self.assertEqual(service.compare_basket(88), compare_result)
        self.assertEqual(service.list_chains(), chains_result)
        self.assertEqual(
            service.download_transparency_files(target_root="data/raw/downloads", limit=2),
            {"success": True},
        )
        self.assertEqual(service.update_basket_item_quantity(88, 42, 4), updated_item)
        self.assertEqual(service.clear_basket(88), 1)
        self.assertEqual(service.get_basket_state(88), basket_state)
        service.remove_basket_item(88, 42)

        load_prices_use_case.execute.assert_called_once_with(load_request)
        add_basket_item_use_case.execute.assert_called_once_with(input_item)
        compare_basket_use_case.execute.assert_called_once_with(88)
        list_chains_use_case.execute.assert_called_once_with()
        download_transparency_use_case.execute.assert_called_once_with(
            target_root="data/raw/downloads",
            chains=None,
            file_types=None,
            when_date=None,
            limit=2,
            include_store_files=None,
            prefer_full_price_files=None,
        )
        update_quantity_use_case.execute.assert_called_once_with(
            basket_id=88,
            item_id=42,
            quantity=4,
        )
        remove_basket_item_use_case.execute.assert_called_once_with(
            basket_id=88,
            item_id=42,
        )
        clear_basket_use_case.execute.assert_called_once_with(basket_id=88)
        get_basket_state_use_case.execute.assert_called_once_with(basket_id=88)


class TestDownloadTransparencyFilesUseCase(unittest.TestCase):
    def test_execute_delegates_to_downloader(self) -> None:
        downloader = Mock()
        expected = {"success": True, "downloaded_files": 3}
        downloader.download_files.return_value = expected

        use_case = DownloadTransparencyFilesUseCase(downloader=downloader)

        result = use_case.execute(
            target_root="data/raw/downloads",
            chains=None,
            file_types=None,
            when_date=None,
            limit=3,
            include_store_files=True,
            prefer_full_price_files=True,
        )

        self.assertEqual(result, expected)
        downloader.download_files.assert_called_once_with(
            target_root="data/raw/downloads",
            chains=None,
            file_types=None,
            when_date=None,
            limit=3,
            include_store_files=True,
            prefer_full_price_files=True,
        )



class TestUpdateBasketItemQuantityUseCase(unittest.TestCase):
    def test_execute_updates_existing_item_quantity(self) -> None:
        repository = Mock()
        existing_item = BasketItem(
            id=9,
            basket_id=100,
            product_id=77,
            input_value="milk",
            input_type="name",
            quantity=1,
            match_status="matched",
        )
        repository.get_by_basket_id.return_value = [existing_item]
        use_case = UpdateBasketItemQuantityUseCase(basket_repository=repository)

        result = use_case.execute(basket_id=100, item_id=9, quantity=3)

        self.assertEqual(result.quantity, 3)
        repository.get_by_basket_id.assert_called_once_with(100)
        repository.update_item.assert_called_once_with(result)

    def test_execute_raises_for_invalid_quantity(self) -> None:
        repository = Mock()
        use_case = UpdateBasketItemQuantityUseCase(basket_repository=repository)

        with self.assertRaises(ValueError):
            use_case.execute(basket_id=100, item_id=9, quantity=0)

        repository.get_by_basket_id.assert_not_called()
        repository.update_item.assert_not_called()

    def test_execute_raises_when_item_is_missing_from_basket(self) -> None:
        repository = Mock()
        repository.get_by_basket_id.return_value = []
        use_case = UpdateBasketItemQuantityUseCase(basket_repository=repository)

        with self.assertRaises(ValueError):
            use_case.execute(basket_id=100, item_id=9, quantity=1)

        repository.update_item.assert_not_called()


class TestRemoveBasketItemUseCase(unittest.TestCase):
    def test_execute_deletes_item_when_present(self) -> None:
        repository = Mock()
        existing_item = BasketItem(
            id=9,
            basket_id=100,
            product_id=77,
            input_value="milk",
            input_type="name",
            quantity=1,
            match_status="matched",
        )
        repository.get_by_basket_id.return_value = [existing_item]
        use_case = RemoveBasketItemUseCase(basket_repository=repository)

        use_case.execute(basket_id=100, item_id=9)

        repository.get_by_basket_id.assert_called_once_with(100)
        repository.delete_item.assert_called_once_with(9)

    def test_execute_raises_for_missing_item(self) -> None:
        repository = Mock()
        repository.get_by_basket_id.return_value = []
        use_case = RemoveBasketItemUseCase(basket_repository=repository)

        with self.assertRaises(ValueError):
            use_case.execute(basket_id=100, item_id=9)

        repository.delete_item.assert_not_called()


class TestClearBasketUseCase(unittest.TestCase):
    def test_execute_delegates_to_repository(self) -> None:
        repository = Mock()
        repository.clear_by_basket_id.return_value = 2
        use_case = ClearBasketUseCase(basket_repository=repository)

        result = use_case.execute(100)

        self.assertEqual(result, 2)
        repository.clear_by_basket_id.assert_called_once_with(100)


class TestGetBasketStateUseCase(unittest.TestCase):
    def test_execute_returns_stable_basket_state_structure(self) -> None:
        repository = Mock()
        repository.get_by_basket_id.return_value = [
            BasketItem(
                id=1,
                basket_id=100,
                product_id=10,
                input_value="bread",
                input_type="name",
                quantity=2,
                match_status="matched",
            ),
            BasketItem(
                id=2,
                basket_id=100,
                product_id=None,
                input_value="unknown",
                input_type="name",
                quantity=1,
                match_status="ambiguous",
                candidate_product_ids=[99, 100],
            ),
        ]
        use_case = GetBasketStateUseCase(basket_repository=repository)

        result = use_case.execute(100)

        self.assertEqual(result["basket_id"], 100)
        self.assertEqual(result["item_count"], 2)
        self.assertEqual(result["items"][0]["id"], 1)
        self.assertEqual(result["items"][1]["match_status"], "ambiguous")
        self.assertEqual(result["items"][0]["candidate_product_ids"], [])
        self.assertEqual(result["items"][1]["candidate_product_ids"], [99, 100])


if __name__ == "__main__":
    unittest.main()
