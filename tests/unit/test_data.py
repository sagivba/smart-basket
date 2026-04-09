"""Unit tests for parser core infrastructure and MVP concrete parsing."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from Modules.data.parser import (
    FileFormat,
    FileParser,
    MalformedFileContentError,
    ParsedPriceRecord,
    ParsedProductRecord,
    ParsingError,
    ParsingErrorCollection,
    ParsingSummary,
    UnsupportedFileFormatError,
    parse_prices_file,
    parse_products_file,
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

    def test_detect_format_missing_suffix_raises(self) -> None:
        with self.assertRaisesRegex(UnsupportedFileFormatError, "<none>"):
            FileParser.detect_format("prices")


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

        summary.record_accepted()
        summary.record_accepted()
        summary.record_rejected()
        summary.add_warning("empty optional brand on row 3")

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

    def test_error_collection_extend_preserves_order(self) -> None:
        collection = FileParser.create_error_collection()
        first = ParsingError(row_number=1, field_name="barcode", message="required")
        second = ParsingError(row_number=2, field_name="price", message="invalid")

        collection.extend([first, second])

        self.assertEqual(collection.count, 2)
        self.assertEqual(collection.errors, [first, second])


class TestProductAndPriceFileParsing(unittest.TestCase):
    def _write_temp_file(self, suffix: str, content: str) -> str:
        with tempfile.NamedTemporaryFile("w", suffix=suffix, encoding="utf-8", delete=False) as handle:
            handle.write(content)
            return handle.name

    def test_parse_products_file_csv_success_with_normalization(self) -> None:
        file_path = self._write_temp_file(
            ".csv",
            "barcode,product_name,brand,unit_name\n"
            "7290012345678,  Milk   1L  ,  DairyCo  , 1L \n",
        )

        records, summary, errors = parse_products_file(file_path)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].barcode, "7290012345678")
        self.assertEqual(records[0].product_name, "Milk 1L")
        self.assertEqual(records[0].normalized_name, "milk 1l")
        self.assertEqual(records[0].brand, "DairyCo")
        self.assertEqual(records[0].unit_name, "1L")
        self.assertEqual(summary.accepted_rows, 1)
        self.assertEqual(summary.rejected_rows, 0)
        self.assertTrue(errors.is_empty())

    def test_parse_prices_file_json_success(self) -> None:
        file_path = self._write_temp_file(
            ".json",
            "["
            '{"chain_code": "CH01", "store_code": "ST10", "barcode": "7290012345678", '
            '"price": "12.50", "currency": "ILS", "price_date": "2026-04-09"}'
            "]",
        )

        records, summary, errors = parse_prices_file(file_path)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].chain_code, "CH01")
        self.assertEqual(records[0].store_code, "ST10")
        self.assertEqual(records[0].barcode, "7290012345678")
        self.assertEqual(records[0].price_text, "12.50")
        self.assertEqual(records[0].currency, "ILS")
        self.assertEqual(records[0].price_date_text, "2026-04-09")
        self.assertEqual(summary.accepted_rows, 1)
        self.assertEqual(summary.rejected_rows, 0)
        self.assertTrue(errors.is_empty())

    def test_parse_products_file_tracks_invalid_row(self) -> None:
        file_path = self._write_temp_file(
            ".csv",
            "barcode,product_name\n"
            "not-a-barcode,Milk\n",
        )

        records, summary, errors = parse_products_file(file_path)

        self.assertEqual(records, [])
        self.assertEqual(summary.accepted_rows, 0)
        self.assertEqual(summary.rejected_rows, 1)
        self.assertEqual(errors.count, 1)
        self.assertEqual(errors.errors[0].row_number, 2)
        self.assertEqual(errors.errors[0].field_name, "barcode")

    def test_parse_prices_file_tracks_invalid_row(self) -> None:
        file_path = self._write_temp_file(
            ".json",
            "["
            '{"chain_code": "CH01", "store_code": "", "barcode": "7290012345678", '
            '"price": "11.90", "currency": "ILS", "price_date": "2026-04-09"}'
            "]",
        )

        records, summary, errors = parse_prices_file(file_path)

        self.assertEqual(records, [])
        self.assertEqual(summary.accepted_rows, 0)
        self.assertEqual(summary.rejected_rows, 1)
        self.assertEqual(errors.count, 1)
        self.assertEqual(errors.errors[0].field_name, "store_code")

    def test_parse_products_file_raises_for_malformed_json_content(self) -> None:
        file_path = self._write_temp_file(".json", "not-json")

        with self.assertRaisesRegex(MalformedFileContentError, "malformed JSON content"):
            parse_products_file(file_path)

    def test_parse_prices_file_raises_for_malformed_content(self) -> None:
        file_path = self._write_temp_file(".csv", "")

        with self.assertRaisesRegex(MalformedFileContentError, "header row"):
            parse_prices_file(file_path)

    def test_parse_products_file_unsupported_format(self) -> None:
        file_path = self._write_temp_file(".xml", "<products></products>")

        with self.assertRaisesRegex(UnsupportedFileFormatError, "unsupported file format"):
            parse_products_file(file_path)


if __name__ == "__main__":
    unittest.main()
