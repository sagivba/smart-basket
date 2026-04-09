"""Core validation helpers for MVP input checks."""

from __future__ import annotations


def validate_barcode(barcode: str) -> str:
    """Validate a simple digit-only barcode and return a normalized value.

    MVP rule: barcode must be a digit string with length between 8 and 14,
    after trimming surrounding whitespace.
    """
    if not isinstance(barcode, str):
        raise TypeError("barcode must be a string")

    normalized = barcode.strip()
    if not normalized:
        raise ValueError("barcode is required")
    if not normalized.isdigit():
        raise ValueError("barcode must contain digits only")
    if not 8 <= len(normalized) <= 14:
        raise ValueError("barcode length must be between 8 and 14 digits")

    return normalized


def validate_quantity(quantity: int) -> int:
    """Validate quantity as a positive integer and return it unchanged."""
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise TypeError("quantity must be an integer")
    if quantity <= 0:
        raise ValueError("quantity must be a positive integer")
    return quantity


def validate_price(price: int | float) -> int | float:
    """Validate price as a non-negative numeric value and return it unchanged."""
    if isinstance(price, bool) or not isinstance(price, (int, float)):
        raise TypeError("price must be a number")
    if price < 0:
        raise ValueError("price must not be negative")
    return price


def validate_required_text(value: str, field_name: str = "value") -> str:
    """Validate a required text field and return a stripped value."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")

    return normalized
