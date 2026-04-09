"""Basket engine matching logic for the MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence

from Modules.models.entities import Product
from Modules.models.results import MatchStatus
from Modules.utils.validators import validate_barcode


class ProductLookupRepository(Protocol):
    """Repository contract required for barcode-based product lookup."""

    def get_by_barcode(self, barcode: str) -> Product | None:
        """Return a product for the given barcode when it exists."""


@dataclass(slots=True)
class BarcodeMatchItem:
    """A single matched barcode input and its resolved product."""

    input_barcode: str
    product_id: int
    product_barcode: str
    product_name: str
    match_status: MatchStatus = MatchStatus.MATCHED


@dataclass(slots=True)
class BarcodeMatchResult:
    """Deterministic barcode matching output for MVP basket inputs."""

    matched_items: list[BarcodeMatchItem] = field(default_factory=list)
    unmatched_items: list[str] = field(default_factory=list)


class BasketEngine:
    """Engine service for direct product matching behavior."""

    def __init__(self, product_repository: ProductLookupRepository) -> None:
        self._product_repository = product_repository

    def match_by_barcodes(self, barcodes: Sequence[str]) -> BarcodeMatchResult:
        """Match barcode inputs directly through repository lookup only."""
        result = BarcodeMatchResult()

        for barcode_input in barcodes:
            barcode = validate_barcode(barcode_input)
            product = self._product_repository.get_by_barcode(barcode)

            if product is None:
                result.unmatched_items.append(barcode)
                continue

            product_id = product.id
            if product_id is None:
                raise ValueError("matched product must include product id")

            result.matched_items.append(
                BarcodeMatchItem(
                    input_barcode=barcode,
                    product_id=product_id,
                    product_barcode=product.barcode,
                    product_name=product.name,
                )
            )

        return result
