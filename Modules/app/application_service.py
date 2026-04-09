"""Application-layer service and use cases for thin orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from Modules.models.entities import BasketItem
from Modules.models.results import BasketComparisonResult


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


@dataclass(slots=True)
class ApplicationService:
    """Thin facade that exposes explicit application-layer use cases."""

    load_prices_use_case: LoadPricesUseCase
    add_basket_item_use_case: AddBasketItemUseCase
    compare_basket_use_case: CompareBasketUseCase
    list_chains_use_case: ListChainsUseCase

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
