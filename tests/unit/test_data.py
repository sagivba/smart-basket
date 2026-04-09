"""Unit tests for parser core infrastructure."""

from __future__ import annotations

import unittest
from pathlib import Path

from Modules.data.parser import (
    FileFormat,
    FileParser,
    ParsedPriceRecord,
    ParsedProductRecord,
    ParsingError,
    ParsingErrorCollection,
    ParsingSummary,
    UnsupportedFileFormatError,
)


class TestParsedRecords(unittest.TestCase):
    def test_parsed_product_record_construction(self) -> None:
        record = ParsedProductRecord(
            source_row_number=3,
            barcode="7290012345678",
            product_name="Milk 1L",
            normalized_name="milk 1l",
            brand="DairyCo",
            unit_name="1L",
        )

        self.assertEqual(record.source_row_number, 3)
        self.assertEqual(record.barcode, "7290012345678")
        self.assertEqual(record.product_name, "Milk 1L")
        self.assertEqual(record.normalized_name, "milk 1l")
        self.assertEqual(record.brand, "DairyCo")
        self.assertEqual(record.unit_name, "1L")

    def test_parsed_price_record_construction(self) -> None:
        record = ParsedPriceRecord(
            source_row_number=12,
            chain_code="CH01",
            store_code="ST10",
            barcode="7290012345678",
            price_text="14.90",
            currency="ILS",
            price_date_text="2026-04-09",
        )

        self.assertEqual(record.source_row_number, 12)
        self.assertEqual(record.chain_code, "CH01")
        self.assertEqual(record.store_code, "ST10")
        self.assertEqual(record.barcode, "7290012345678")
        self.assertEqual(record.price_text, "14.90")
        self.assertEqual(record.currency, "ILS")
        self.assertEqual(record.price_date_text, "2026-04-09")


class TestFileFormatDetection(unittest.TestCase):
    def test_detect_format_csv_suffix(self) -> None:
        self.assertEqual(FileParser.detect_format("products.csv"), FileFormat.CSV)

    def test_detect_format_json_suffix_case_insensitive(self) -> None:
        self.assertEqual(FileParser.detect_format(Path("prices.JSON")), FileFormat.JSON)

    def test_detect_format_unsupported_suffix_raises(self) -> None:
        with self.assertRaisesRegex(UnsupportedFileFormatError, "unsupported file format"):
            FileParser.detect_format("stores.xml")


class TestParsingSummaryAndErrors(unittest.TestCase):
    def test_create_summary_tracks_minimal_outcomes(self) -> None:
        summary = FileParser.create_summary("products.csv")

        self.assertIsInstance(summary, ParsingSummary)
        self.assertEqual(summary.file_path, Path("products.csv"))
        self.assertEqual(summary.file_format, FileFormat.CSV)
        self.assertEqual(summary.accepted_rows, 0)
        self.assertEqual(summary.rejected_rows, 0)
        self.assertEqual(summary.total_rows, 0)
        self.assertEqual(summary.warnings, [])

        summary.accepted_rows += 2
        summary.rejected_rows += 1
        summary.warnings.append("empty optional brand on row 3")

        self.assertEqual(summary.total_rows, 3)
        self.assertEqual(summary.warnings, ["empty optional brand on row 3"])

    def test_error_collection_add_and_count(self) -> None:
        collection = FileParser.create_error_collection()

        self.assertIsInstance(collection, ParsingErrorCollection)
        self.assertTrue(collection.is_empty())
        self.assertEqual(collection.count, 0)

        error = ParsingError(
            row_number=5,
            field_name="barcode",
            message="barcode is required",
            raw_value="",
        )
        collection.add(error)

        self.assertFalse(collection.is_empty())
        self.assertEqual(collection.count, 1)
        self.assertEqual(collection.errors[0], error)


if __name__ == "__main__":
    unittest.main()
