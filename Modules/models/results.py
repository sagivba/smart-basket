"""Result models and enums for basket comparison outputs."""

from dataclasses import dataclass, field
from enum import Enum


class MatchStatus(str, Enum):
    """Status of an input basket item after matching."""

    MATCHED = "matched"
    UNMATCHED = "unmatched"
    AMBIGUOUS = "ambiguous"


class AvailabilityStatus(str, Enum):
    """Availability status of a matched product in a chain."""

    FOUND = "found"
    MISSING = "missing"


@dataclass(slots=True)
class BasketLineResult:
    """Line-level basket result for a single product in a single chain."""

    product_id: int | None
    product_name: str
    barcode: str | None
    quantity: int
    unit_price: float | None
    line_price: float | None
    availability_status: AvailabilityStatus

    def __post_init__(self) -> None:
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("quantity must be a positive integer")

        if self.unit_price is not None and self.unit_price < 0:
            raise ValueError("unit_price must not be negative")

        if self.line_price is not None and self.line_price < 0:
            raise ValueError("line_price must not be negative")


@dataclass(slots=True)
class ChainComparisonResult:
    """Comparison result for a single retail chain."""

    chain_id: int
    chain_name: str
    total_price: float
    found_items_count: int
    missing_items_count: int
    is_complete_basket: bool
    basket_lines: list[BasketLineResult] = field(default_factory=list)
    missing_items: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.total_price < 0:
            raise ValueError("total_price must not be negative")

        if self.found_items_count < 0:
            raise ValueError("found_items_count must not be negative")

        if self.missing_items_count < 0:
            raise ValueError("missing_items_count must not be negative")

        if self.is_complete_basket and self.missing_items_count != 0:
            raise ValueError(
                "is_complete_basket cannot be true when missing_items_count is non-zero"
            )


@dataclass(slots=True)
class BasketComparisonResult:
    """Top-level result for comparing a basket across chains."""

    ranked_chains: list[ChainComparisonResult] = field(default_factory=list)
    unmatched_items: list[str] = field(default_factory=list)
