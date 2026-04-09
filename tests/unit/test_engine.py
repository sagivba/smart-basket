"""Unit tests for engine name-based product matching."""

from __future__ import annotations

import unittest

from Modules.engine.basket_engine import BasketEngine
from Modules.models.entities import Product
from Modules.models.results import MatchStatus


class TestBasketEngineNameMatching(unittest.TestCase):
    def _product(self, *, product_id: int, name: str, normalized_name: str, barcode: str) -> Product:
        return Product(
            id=product_id,
            barcode=barcode,
            name=name,
            normalized_name=normalized_name,
            brand=None,
            unit_name=None,
        )

    def test_unambiguous_normalized_name_match_returns_single_matched_product(self) -> None:
        products = [
            self._product(
                product_id=10,
                name="Milk 1L",
                normalized_name="milk 1l",
                barcode="7290000000010",
            ),
            self._product(
                product_id=11,
                name="Bread",
                normalized_name="bread",
                barcode="7290000000011",
            ),
        ]

        result = BasketEngine.match_product_name("  MILK   1L ", products)

        self.assertEqual(result.status, MatchStatus.MATCHED)
        self.assertIsNotNone(result.matched_product)
        self.assertEqual(result.matched_product.id, 10)
        self.assertEqual(result.candidate_products, [])

    def test_ambiguous_normalized_name_match_returns_candidate_list(self) -> None:
        products = [
            self._product(
                product_id=40,
                name="Tomato Paste 500g",
                normalized_name="tomato paste 500g",
                barcode="7290000000040",
            ),
            self._product(
                product_id=30,
                name="Tomato Paste 500G",
                normalized_name="tomato paste 500g",
                barcode="7290000000030",
            ),
        ]

        result = BasketEngine.match_product_name("tomato   paste 500g", products)

        self.assertEqual(result.status, MatchStatus.AMBIGUOUS)
        self.assertIsNone(result.matched_product)
        self.assertEqual([candidate.id for candidate in result.candidate_products], [30, 40])

    def test_unknown_name_is_marked_as_unmatched(self) -> None:
        products = [
            self._product(
                product_id=20,
                name="Eggs",
                normalized_name="eggs",
                barcode="7290000000020",
            )
        ]

        result = BasketEngine.match_product_name("Chocolate Bar", products)

        self.assertEqual(result.status, MatchStatus.UNMATCHED)
        self.assertIsNone(result.matched_product)
        self.assertEqual(result.candidate_products, [])

    def test_match_result_to_dict_has_deterministic_structure(self) -> None:
        products = [
            self._product(
                product_id=50,
                name="Yogurt",
                normalized_name="yogurt",
                barcode="7290000000050",
            )
        ]

        result_dict = BasketEngine.match_product_name("Yogurt", products).to_dict()

        self.assertEqual(
            list(result_dict.keys()),
            [
                "input_name",
                "normalized_input_name",
                "status",
                "matched_product",
                "candidate_products",
            ],
        )
        self.assertEqual(result_dict["input_name"], "Yogurt")
        self.assertEqual(result_dict["normalized_input_name"], "yogurt")
        self.assertEqual(result_dict["status"], MatchStatus.MATCHED.value)


if __name__ == "__main__":
    unittest.main()
