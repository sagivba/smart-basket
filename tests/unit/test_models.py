import unittest

from Modules.models.results import (
    AvailabilityStatus,
    BasketComparisonResult,
    BasketLineResult,
    ChainComparisonResult,
    MatchStatus,
)


class TestEnums(unittest.TestCase):
    def test_match_status_values(self) -> None:
        self.assertEqual(MatchStatus.MATCHED.value, "matched")
        self.assertEqual(MatchStatus.UNMATCHED.value, "unmatched")
        self.assertEqual(MatchStatus.AMBIGUOUS.value, "ambiguous")

    def test_availability_status_values(self) -> None:
        self.assertEqual(AvailabilityStatus.FOUND.value, "found")
        self.assertEqual(AvailabilityStatus.MISSING.value, "missing")


class TestBasketLineResult(unittest.TestCase):
    def test_valid_construction(self) -> None:
        result = BasketLineResult(
            product_id=101,
            product_name="Milk",
            barcode="1234567890123",
            quantity=2,
            unit_price=3.5,
            line_price=7.0,
            availability_status=AvailabilityStatus.FOUND,
        )

        self.assertEqual(result.product_id, 101)
        self.assertEqual(result.quantity, 2)
        self.assertEqual(result.line_price, 7.0)

    def test_raises_for_non_positive_quantity(self) -> None:
        with self.assertRaises(ValueError):
            BasketLineResult(
                product_id=1,
                product_name="Bread",
                barcode="111",
                quantity=0,
                unit_price=2.0,
                line_price=2.0,
                availability_status=AvailabilityStatus.FOUND,
            )

    def test_raises_for_negative_prices(self) -> None:
        with self.assertRaises(ValueError):
            BasketLineResult(
                product_id=1,
                product_name="Bread",
                barcode="111",
                quantity=1,
                unit_price=-1.0,
                line_price=1.0,
                availability_status=AvailabilityStatus.FOUND,
            )

        with self.assertRaises(ValueError):
            BasketLineResult(
                product_id=1,
                product_name="Bread",
                barcode="111",
                quantity=1,
                unit_price=1.0,
                line_price=-1.0,
                availability_status=AvailabilityStatus.FOUND,
            )


class TestChainComparisonResult(unittest.TestCase):
    def _line(self) -> BasketLineResult:
        return BasketLineResult(
            product_id=1,
            product_name="Milk",
            barcode="123",
            quantity=1,
            unit_price=5.0,
            line_price=5.0,
            availability_status=AvailabilityStatus.FOUND,
        )

    def test_valid_construction(self) -> None:
        result = ChainComparisonResult(
            chain_id=10,
            chain_name="Chain A",
            total_price=5.0,
            found_items_count=1,
            missing_items_count=0,
            is_complete_basket=True,
            basket_lines=[self._line()],
            missing_items=[],
        )

        self.assertEqual(result.chain_id, 10)
        self.assertTrue(result.is_complete_basket)
        self.assertEqual(len(result.basket_lines), 1)

    def test_raises_for_negative_total_price(self) -> None:
        with self.assertRaises(ValueError):
            ChainComparisonResult(
                chain_id=1,
                chain_name="Chain A",
                total_price=-0.01,
                found_items_count=0,
                missing_items_count=0,
                is_complete_basket=True,
            )

    def test_raises_for_negative_counts(self) -> None:
        with self.assertRaises(ValueError):
            ChainComparisonResult(
                chain_id=1,
                chain_name="Chain A",
                total_price=0.0,
                found_items_count=-1,
                missing_items_count=0,
                is_complete_basket=False,
            )

        with self.assertRaises(ValueError):
            ChainComparisonResult(
                chain_id=1,
                chain_name="Chain A",
                total_price=0.0,
                found_items_count=0,
                missing_items_count=-1,
                is_complete_basket=False,
            )

    def test_raises_for_incoherent_complete_basket_state(self) -> None:
        with self.assertRaises(ValueError):
            ChainComparisonResult(
                chain_id=1,
                chain_name="Chain A",
                total_price=0.0,
                found_items_count=1,
                missing_items_count=1,
                is_complete_basket=True,
                missing_items=["Eggs"],
            )


class TestBasketComparisonResult(unittest.TestCase):
    def test_valid_construction(self) -> None:
        chain_result = ChainComparisonResult(
            chain_id=1,
            chain_name="Chain A",
            total_price=10.0,
            found_items_count=2,
            missing_items_count=0,
            is_complete_basket=True,
        )

        result = BasketComparisonResult(
            ranked_chains=[chain_result],
            unmatched_items=["unknown barcode"],
        )

        self.assertEqual(len(result.ranked_chains), 1)
        self.assertEqual(result.unmatched_items, ["unknown barcode"])


if __name__ == "__main__":
    unittest.main()
