"""Utility helpers for deterministic text normalization."""

from __future__ import annotations

import re

_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_whitespace(value: str) -> str:
    """Trim surrounding whitespace and collapse internal whitespace to one space."""
    stripped_value = value.strip()
    if not stripped_value:
        return ""

    return _WHITESPACE_PATTERN.sub(" ", stripped_value)


def normalize_text(value: str) -> str:
    """Normalize text for comparison-oriented usage in the MVP."""
    return normalize_whitespace(value).lower()


def normalize_product_name(value: str) -> str:
    """Normalize product-name input for future exact string comparison."""
    return normalize_text(value)
