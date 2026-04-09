import unittest

from Modules.utils.text_utils import (
    normalize_product_name,
    normalize_text,
    normalize_whitespace,
)
from Modules.utils.validators import (
    validate_barcode,
    validate_price,
    validate_quantity,
    validate_required_text,
)


class TestNormalizeWhitespace(unittest.TestCase):
    def test_trims_surrounding_whitespace(self) -> None:
        self.assertEqual(normalize_whitespace("  milk  "), "milk")

    def test_collapses_repeated_internal_whitespace(self) -> None:
        self.assertEqual(normalize_whitespace("milk   2%\t\nlarge"), "milk 2% large")

    def test_returns_empty_string_for_whitespace_only_input(self) -> None:
        self.assertEqual(normalize_whitespace("   \t\n  "), "")

    def test_returns_empty_string_for_empty_input(self) -> None:
        self.assertEqual(normalize_whitespace(""), "")

    def test_leaves_already_normalized_whitespace_unchanged(self) -> None:
        self.assertEqual(normalize_whitespace("whole milk"), "whole milk")


class TestNormalizeText(unittest.TestCase):
    def test_normalizes_whitespace_and_lowercase(self) -> None:
        self.assertEqual(normalize_text("  Whole   MILK  "), "whole milk")

    def test_returns_empty_string_for_empty_input(self) -> None:
        self.assertEqual(normalize_text(""), "")


class TestNormalizeProductName(unittest.TestCase):
    def test_normalizes_simple_product_name(self) -> None:
        self.assertEqual(normalize_product_name("  Chocolate   Bar 100G "), "chocolate bar 100g")

    def test_keeps_punctuation_characters(self) -> None:
        self.assertEqual(normalize_product_name("Tomato-Paste, 500g"), "tomato-paste, 500g")


class TestValidateBarcode(unittest.TestCase):
    def test_valid_barcode_returns_trimmed_value(self) -> None:
        self.assertEqual(validate_barcode(" 12345678 "), "12345678")

    def test_invalid_barcode_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            validate_barcode("12ab5678")


class TestValidateQuantity(unittest.TestCase):
    def test_valid_quantity_returns_value(self) -> None:
        self.assertEqual(validate_quantity(3), 3)

    def test_zero_quantity_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            validate_quantity(0)

    def test_negative_quantity_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            validate_quantity(-1)


class TestValidatePrice(unittest.TestCase):
    def test_valid_non_negative_price_returns_value(self) -> None:
        self.assertEqual(validate_price(0.0), 0.0)

    def test_negative_price_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            validate_price(-0.01)


class TestValidateRequiredText(unittest.TestCase):
    def test_valid_required_text_returns_trimmed_value(self) -> None:
        self.assertEqual(validate_required_text("  Milk  ", field_name="name"), "Milk")

    def test_empty_required_text_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            validate_required_text("", field_name="name")

    def test_whitespace_only_required_text_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            validate_required_text("   \t", field_name="name")


if __name__ == "__main__":
    unittest.main()
