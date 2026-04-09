import unittest

from Modules.utils.text_utils import (
    normalize_product_name,
    normalize_text,
    normalize_whitespace,
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


if __name__ == "__main__":
    unittest.main()
