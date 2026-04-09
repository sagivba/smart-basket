"""Unit tests for utility validators."""

import unittest

from Modules.utils.validators import (
    validate_barcode,
    validate_price,
    validate_quantity,
    validate_required_text,
)


class TestValidators(unittest.TestCase):
    def test_validate_quantity_valid_positive_integer(self) -> None:
        self.assertEqual(validate_quantity(3), 3)

    def test_validate_quantity_rejects_zero(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive integer"):
            validate_quantity(0)

    def test_validate_quantity_rejects_negative(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive integer"):
            validate_quantity(-1)

    def test_validate_price_valid_non_negative(self) -> None:
        self.assertEqual(validate_price(0.0), 0.0)
        self.assertEqual(validate_price(12.5), 12.5)

    def test_validate_price_rejects_negative(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be negative"):
            validate_price(-0.01)

    def test_validate_required_text_valid_non_empty(self) -> None:
        self.assertEqual(validate_required_text("  Milk  ", "name"), "Milk")

    def test_validate_required_text_rejects_empty(self) -> None:
        with self.assertRaisesRegex(ValueError, "name is required"):
            validate_required_text("", "name")

    def test_validate_required_text_rejects_whitespace_only(self) -> None:
        with self.assertRaisesRegex(ValueError, "name is required"):
            validate_required_text("   ", "name")

    def test_validate_barcode_valid_simple_input(self) -> None:
        self.assertEqual(validate_barcode(" 12345678 "), "12345678")

    def test_validate_barcode_rejects_invalid_characters(self) -> None:
        with self.assertRaisesRegex(ValueError, "digits only"):
            validate_barcode("12A45678")


if __name__ == "__main__":
    unittest.main()
