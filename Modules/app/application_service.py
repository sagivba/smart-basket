"""Application-layer service and use cases for thin orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from Modules.models.entities import BasketItem
from Modules.models.results import BasketComparisonResult
from Modules.utils.validators import validate_quantity


class PriceLoaderProtocol(Protocol):
    """Protocol for price loading collaborators in the data layer."""

    def load_prices(self, load_request: Any) -> Any:
        """Load price data according to a concrete load request object."""


class BasketRepositoryProtocol(Protocol):
    """Protocol for basket persistence collaborators."""

    def add_item(self, item: BasketItem) -> BasketItem:
        """Persist one basket item."""

    def get_by_basket_id(self, basket_id: int) -> list[BasketItem]:
        """Return all basket items for one basket."""

    def update_item(self, item: BasketItem) -> None:
        """Update one basket item by identifier."""

    def delete_item(self, item_id: int) -> None:
        """Delete one basket item by identifier."""

    def clear_by_basket_id(self, basket_id: int) -> int:
        """Delete all items in the requested basket and return deleted count."""


class BasketComparisonServiceProtocol(Protocol):
    """Protocol for basket comparison engine collaborator."""

    def compare_basket(self, basket_items: list[BasketItem]) -> BasketComparisonResult:
        """Compare basket items across chains."""


class ChainReadRepositoryProtocol(Protocol):
    """Protocol for chain listing collaborator."""

    def list_chains(self) -> list[Any]:
        """Return available chains."""


@dataclass(slots=True)
class LoadPricesUseCase:
    """Application use case that orchestrates price loading."""

    loader: PriceLoaderProtocol

    def execute(self, load_request: Any) -> Any:
        """Run the price-loading workflow by delegating to the data loader."""
        return self.loader.load_prices(load_request)


@dataclass(slots=True)
class AddBasketItemUseCase:
    """Application use case that orchestrates basket-item persistence."""

    basket_repository: BasketRepositoryProtocol

    def execute(self, item: BasketItem) -> BasketItem:
        """Persist a basket item and return the stored entity."""
        return self.basket_repository.add_item(item)


@dataclass(slots=True)
class CompareBasketUseCase:
    """Application use case that orchestrates basket comparison."""

    basket_repository: BasketRepositoryProtocol
    comparison_service: BasketComparisonServiceProtocol

    def execute(self, basket_id: int) -> BasketComparisonResult:
        """Load basket items and run comparison through the engine service."""
        basket_items = self.basket_repository.get_by_basket_id(basket_id)
        return self.comparison_service.compare_basket(basket_items)


@dataclass(slots=True)
class ListChainsUseCase:
    """Application use case that orchestrates chain listing retrieval."""

    chain_repository: ChainReadRepositoryProtocol

    def execute(self) -> list[Any]:
        """Return available chains from persistence read model."""
        return self.chain_repository.list_chains()




class TransparencyDownloaderProtocol(Protocol):
    """Protocol for raw transparency-file download collaborator."""

    def download_files(
        self,
        target_root: str | Any,
        when_date: Any = None,
        limit: int | None = None,
        include_store_files: bool = True,
        prefer_full_price_files: bool = True,
    ) -> Any:
        """Download raw transparency files for supported chains."""


@dataclass(slots=True)
class DownloadTransparencyFilesUseCase:
    """Application use case that orchestrates remote raw-file downloads."""

    downloader: TransparencyDownloaderProtocol

    def execute(
        self,
        target_root: str | Any = "data/raw/downloads",
        when_date: Any = None,
        limit: int | None = None,
        include_store_files: bool = True,
        prefer_full_price_files: bool = True,
    ) -> Any:
        """Run the remote download workflow via the data-layer downloader."""
        return self.downloader.download_files(
            target_root=target_root,
            when_date=when_date,
            limit=limit,
            include_store_files=include_store_files,
            prefer_full_price_files=prefer_full_price_files,
        )


@dataclass(slots=True)
class UpdateBasketItemQuantityUseCase:
    """Application use case that orchestrates quantity updates."""

    basket_repository: BasketRepositoryProtocol

    def execute(self, basket_id: int, item_id: int, quantity: int) -> BasketItem:
        """Update one basket item's quantity and return the updated item."""
        validated_quantity = validate_quantity(quantity)
        basket_items = self.basket_repository.get_by_basket_id(basket_id)
        existing_item = next((item for item in basket_items if item.id == item_id), None)
        if existing_item is None:
            raise ValueError(f"basket item {item_id} was not found in basket {basket_id}")

        updated_item = BasketItem(
            id=existing_item.id,
            basket_id=existing_item.basket_id,
            product_id=existing_item.product_id,
            input_value=existing_item.input_value,
            input_type=existing_item.input_type,
            quantity=validated_quantity,
            match_status=existing_item.match_status,
            candidate_product_ids=list(existing_item.candidate_product_ids),
        )
        self.basket_repository.update_item(updated_item)
        return updated_item


@dataclass(slots=True)
class RemoveBasketItemUseCase:
    """Application use case that orchestrates basket-item removal."""

    basket_repository: BasketRepositoryProtocol

    def execute(self, basket_id: int, item_id: int) -> None:
        """Remove one basket item when it exists in the requested basket."""
        basket_items = self.basket_repository.get_by_basket_id(basket_id)
        existing_item = next((item for item in basket_items if item.id == item_id), None)
        if existing_item is None:
            raise ValueError(f"basket item {item_id} was not found in basket {basket_id}")
        self.basket_repository.delete_item(item_id)


@dataclass(slots=True)
class ClearBasketUseCase:
    """Application use case that orchestrates full basket clearing."""

    basket_repository: BasketRepositoryProtocol

    def execute(self, basket_id: int) -> int:
        """Delete all basket items and return the number of deleted items."""
        return self.basket_repository.clear_by_basket_id(basket_id)


@dataclass(slots=True)
class GetBasketStateUseCase:
    """Application use case that returns the current basket state."""

    basket_repository: BasketRepositoryProtocol

    def execute(self, basket_id: int) -> dict[str, Any]:
        """Load basket items and return a stable structure for consumers."""
        basket_items = self.basket_repository.get_by_basket_id(basket_id)
        return {
            "basket_id": basket_id,
            "item_count": len(basket_items),
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "input_value": item.input_value,
                    "input_type": item.input_type,
                    "quantity": item.quantity,
                    "match_status": item.match_status,
                    "candidate_product_ids": list(item.candidate_product_ids),
                }
                for item in basket_items
            ],
        }


@dataclass(slots=True)
class ApplicationService:
    """Thin facade that exposes explicit application-layer use cases."""

    load_prices_use_case: LoadPricesUseCase
    add_basket_item_use_case: AddBasketItemUseCase
    compare_basket_use_case: CompareBasketUseCase
    list_chains_use_case: ListChainsUseCase
    download_transparency_files_use_case: DownloadTransparencyFilesUseCase
    update_basket_item_quantity_use_case: UpdateBasketItemQuantityUseCase
    remove_basket_item_use_case: RemoveBasketItemUseCase
    clear_basket_use_case: ClearBasketUseCase
    get_basket_state_use_case: GetBasketStateUseCase

    def load_prices(self, load_request: Any) -> Any:
        """Execute the load-prices use case."""
        return self.load_prices_use_case.execute(load_request)

    def add_basket_item(self, item: BasketItem) -> BasketItem:
        """Execute the add-basket-item use case."""
        return self.add_basket_item_use_case.execute(item)

    def compare_basket(self, basket_id: int) -> BasketComparisonResult:
        """Execute the compare-basket use case."""
        return self.compare_basket_use_case.execute(basket_id)

    def list_chains(self) -> list[Any]:
        """Execute the list-chains use case."""
        return self.list_chains_use_case.execute()

    def download_transparency_files(
        self,
        target_root: str | Any = "data/raw/downloads",
        when_date: Any = None,
        limit: int | None = None,
        include_store_files: bool = True,
        prefer_full_price_files: bool = True,
    ) -> Any:
        """Execute the remote transparency-files download use case."""
        return self.download_transparency_files_use_case.execute(
            target_root=target_root,
            when_date=when_date,
            limit=limit,
            include_store_files=include_store_files,
            prefer_full_price_files=prefer_full_price_files,
        )

    def update_basket_item_quantity(
        self, basket_id: int, item_id: int, quantity: int
    ) -> BasketItem:
        """Execute the update-basket-item-quantity use case."""
        return self.update_basket_item_quantity_use_case.execute(
            basket_id=basket_id,
            item_id=item_id,
            quantity=quantity,
        )

    def remove_basket_item(self, basket_id: int, item_id: int) -> None:
        """Execute the remove-basket-item use case."""
        self.remove_basket_item_use_case.execute(basket_id=basket_id, item_id=item_id)

    def clear_basket(self, basket_id: int) -> int:
        """Execute the clear-basket use case."""
        return self.clear_basket_use_case.execute(basket_id=basket_id)

    def get_basket_state(self, basket_id: int) -> dict[str, Any]:
        """Execute the get-basket-state use case."""
        return self.get_basket_state_use_case.execute(basket_id=basket_id)
