"""Basket engine matching utilities for MVP product-name matching."""

from __future__ import annotations

from dataclasses import dataclass, field

from Modules.models.entities import Product
from Modules.models.results import MatchStatus
from Modules.utils.text_utils import normalize_product_name


@dataclass(slots=True)
class NameMatchResult:
    """Structured result for normalized-name matching."""

    input_name: str
    normalized_input_name: str
    status: MatchStatus
    matched_product: Product | None = None
    candidate_products: list[Product] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic dictionary shape for callers and tests."""
        return {
            "input_name": self.input_name,
            "normalized_input_name": self.normalized_input_name,
            "status": self.status.value,
            "matched_product": self.matched_product,
            "candidate_products": self.candidate_products,
        }


class ProductMatcher:
    """Matches basket name inputs against products by normalized name."""

    @staticmethod
    def match_by_normalized_name(input_name: str, products: list[Product]) -> NameMatchResult:
        """Match by exact normalized name and return matched, ambiguous, or unmatched."""
        normalized_input_name = normalize_product_name(input_name)
        candidates = [
            product
            for product in products
            if product.normalized_name == normalized_input_name
        ]
        sorted_candidates = ProductMatcher._sorted_candidates(candidates)

        if len(sorted_candidates) == 1:
            return NameMatchResult(
                input_name=input_name,
                normalized_input_name=normalized_input_name,
                status=MatchStatus.MATCHED,
                matched_product=sorted_candidates[0],
                candidate_products=[],
            )

        if len(sorted_candidates) > 1:
            return NameMatchResult(
                input_name=input_name,
                normalized_input_name=normalized_input_name,
                status=MatchStatus.AMBIGUOUS,
                matched_product=None,
                candidate_products=sorted_candidates,
            )

        return NameMatchResult(
            input_name=input_name,
            normalized_input_name=normalized_input_name,
            status=MatchStatus.UNMATCHED,
            matched_product=None,
            candidate_products=[],
        )

    @staticmethod
    def _sorted_candidates(candidates: list[Product]) -> list[Product]:
        """Return deterministic candidate ordering for ambiguous results."""
        return sorted(
            candidates,
            key=lambda product: (
                product.id is None,
                product.id if product.id is not None else 0,
                product.barcode,
                product.name,
            ),
        )


class BasketEngine:
    """Engine facade for basket matching behavior in MVP."""

    @staticmethod
    def match_product_name(input_name: str, products: list[Product]) -> NameMatchResult:
        """Delegate name-based matching to the product matcher."""
        return ProductMatcher.match_by_normalized_name(input_name=input_name, products=products)
