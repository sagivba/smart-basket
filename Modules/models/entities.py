"""Core domain entities for the basket comparison MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation


def _strip_text(value: str | None, field_name: str, *, allow_none: bool = False) -> str | None:
    """Normalize text by stripping surrounding whitespace."""
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"{field_name} is required")

    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    return value.strip()


@dataclass(slots=True)
class Product:
    """Represents a product that can be matched in a basket."""

    id: int | None
    barcode: str
    name: str
    normalized_name: str
    brand: str | None = None
    unit_name: str | None = None

    def __post_init__(self) -> None:
        self.barcode = _strip_text(self.barcode, "barcode")
        self.name = _strip_text(self.name, "name")
        self.normalized_name = _strip_text(self.normalized_name, "normalized_name")
        self.brand = _strip_text(self.brand, "brand", allow_none=True)
        self.unit_name = _strip_text(self.unit_name, "unit_name", allow_none=True)


@dataclass(slots=True)
class Chain:
    """Represents a retail chain."""

    id: int | None
    chain_code: str
    name: str

    def __post_init__(self) -> None:
        self.chain_code = _strip_text(self.chain_code, "chain_code")
        self.name = _strip_text(self.name, "name")


@dataclass(slots=True)
class Store:
    """Represents a store that belongs to a chain."""

    id: int | None
    chain_id: int
    store_code: str
    name: str
    city: str | None = None
    address: str | None = None
    is_active: bool = True

    def __post_init__(self) -> None:
        self.store_code = _strip_text(self.store_code, "store_code")
        self.name = _strip_text(self.name, "name")
        self.city = _strip_text(self.city, "city", allow_none=True)
        self.address = _strip_text(self.address, "address", allow_none=True)


@dataclass(slots=True)
class Price:
    """Represents a product price observation at a chain/store."""

    id: int | None
    product_id: int
    chain_id: int
    store_id: int
    price: Decimal
    currency: str
    price_date: date
    source_file: str | None = None

    def __post_init__(self) -> None:
        try:
            self.price = Decimal(str(self.price))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("price must be a valid number") from exc

        if self.price < 0:
            raise ValueError("price must not be negative")

        self.currency = _strip_text(self.currency, "currency")
        self.source_file = _strip_text(self.source_file, "source_file", allow_none=True)


@dataclass(slots=True)
class BasketItem:
    """Represents a single input line in a basket."""

    id: int | None
    basket_id: int
    product_id: int | None
    input_value: str
    input_type: str
    quantity: int
    match_status: str
    candidate_product_ids: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.input_value = _strip_text(self.input_value, "input_value")
        self.input_type = _strip_text(self.input_type, "input_type")
        self.match_status = _strip_text(self.match_status, "match_status")

        if not isinstance(self.quantity, int):
            raise TypeError("quantity must be an integer")

        if self.quantity <= 0:
            raise ValueError("quantity must be a positive integer")

        if not isinstance(self.candidate_product_ids, list):
            raise TypeError("candidate_product_ids must be a list")

        normalized_candidate_ids: list[int] = []
        for candidate_id in self.candidate_product_ids:
            if not isinstance(candidate_id, int) or isinstance(candidate_id, bool):
                raise TypeError("candidate_product_ids must contain integers")
            if candidate_id <= 0:
                raise ValueError("candidate_product_ids must contain positive integers")
            normalized_candidate_ids.append(candidate_id)
        self.candidate_product_ids = normalized_candidate_ids
