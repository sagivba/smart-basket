"""Unit tests for data-layer parsing infrastructure and loader orchestration."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from Modules.data.data_loader import PriceDataLoader
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
from Modules.db.database import create_schema


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


class TestPriceDataLoader(unittest.TestCase):
    def setUp(self) -> None:
        import sqlite3

        self.connection = sqlite3.connect(":memory:")
        create_schema(self.connection)
        self.loader = PriceDataLoader(self.connection)

    def tearDown(self) -> None:
        self.connection.close()

    def test_load_products_append_mode_preserves_existing_rows(self) -> None:
        self.connection.execute(
            "INSERT INTO products (barcode, name, normalized_name) VALUES (?, ?, ?)",
            ("111", "Existing Product", "existing product"),
        )

        parsed_products = [
            {
                "barcode": "222",
                "product_name": "New Product",
                "normalized_name": "new product",
                "brand": "BrandX",
                "unit_name": "1 unit",
            }
        ]
        summary = ParsingSummary(file_path=Path("products.csv"), file_format=FileFormat.CSV)

        with patch(
            "Modules.data.data_loader.parser.parse_products_file",
            return_value=(parsed_products, summary),
            create=True,
        ):
            result = self.loader.load_products("products.csv", mode="append")

        count = self.connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        self.assertEqual(count, 2)
        self.assertEqual(result.accepted_count, 1)
        self.assertEqual(result.rejected_count, 0)
        self.assertTrue(result.success)

    def test_load_products_replace_mode_clears_existing_rows(self) -> None:
        self.connection.execute(
            "INSERT INTO products (barcode, name, normalized_name) VALUES (?, ?, ?)",
            ("111", "Old Product", "old product"),
        )

        parsed_products = [
            {
                "barcode": "999",
                "product_name": "Replacement",
                "normalized_name": "replacement",
            }
        ]

        with patch(
            "Modules.data.data_loader.parser.parse_products_file",
            return_value=(parsed_products, None),
            create=True,
        ):
            result = self.loader.load_products("products.csv", mode="replace")

        rows = self.connection.execute(
            "SELECT barcode FROM products ORDER BY barcode"
        ).fetchall()
        self.assertEqual(rows, [("999",)])
        self.assertEqual(result.accepted_count, 1)
        self.assertEqual(result.rejected_count, 0)

    def test_load_stores_append_and_replace_modes(self) -> None:
        first_batch = [
            {
                "chain_code": "CH1",
                "chain_name": "Chain One",
                "store_code": "S1",
                "store_name": "Store One",
                "city": "City A",
                "address": "Addr A",
                "is_active": True,
            }
        ]
        second_batch = [
            {
                "chain_code": "CH1",
                "chain_name": "Chain One",
                "store_code": "S2",
                "store_name": "Store Two",
            }
        ]

        with patch(
            "Modules.data.data_loader.parser.parse_stores_file",
            return_value=(first_batch, None),
            create=True,
        ):
            append_result = self.loader.load_stores("stores.csv", mode="append")

        with patch(
            "Modules.data.data_loader.parser.parse_stores_file",
            return_value=(second_batch, None),
            create=True,
        ):
            replace_result = self.loader.load_stores("stores.csv", mode="replace")

        rows = self.connection.execute(
            "SELECT store_code FROM stores ORDER BY store_code"
        ).fetchall()
        self.assertEqual(rows, [("S2",)])
        self.assertEqual(append_result.accepted_count, 1)
        self.assertEqual(replace_result.accepted_count, 1)

    def test_load_prices_accepts_valid_rows_and_rejects_missing_relations(self) -> None:
        self.connection.execute(
            "INSERT INTO products (id, barcode, name, normalized_name) VALUES (?, ?, ?, ?)",
            (1, "111", "Milk", "milk"),
        )
        self.connection.execute(
            "INSERT INTO chains (id, chain_code, name) VALUES (?, ?, ?)",
            (1, "CH1", "Chain One"),
        )
        self.connection.execute(
            "INSERT INTO stores (id, chain_id, store_code, name, is_active) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "S1", "Store One", 1),
        )

        parsed_prices = [
            {
                "barcode": "111",
                "chain_code": "CH1",
                "store_code": "S1",
                "price_text": "10.50",
                "currency": "ILS",
                "price_date_text": "2026-04-09",
            },
            {
                "barcode": "999",
                "chain_code": "CH1",
                "store_code": "S1",
                "price_text": "12.00",
                "currency": "ILS",
                "price_date_text": "2026-04-09",
            },
        ]

        with patch(
            "Modules.data.data_loader.parser.parse_prices_file",
            return_value=(parsed_prices, None),
            create=True,
        ):
            result = self.loader.load_prices("prices.csv", mode="append")

        count = self.connection.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
        self.assertEqual(count, 1)
        self.assertEqual(result.accepted_count, 1)
        self.assertEqual(result.rejected_count, 1)
        self.assertFalse(result.success)

    def test_load_result_summary_includes_parser_counts_and_warnings(self) -> None:
        parsed_products = [
            {
                "barcode": "333",
                "product_name": "Summary Product",
                "normalized_name": "summary product",
            }
        ]
        summary = ParsingSummary(
            file_path=Path("products.csv"),
            file_format=FileFormat.CSV,
            accepted_rows=2,
            rejected_rows=1,
            warnings=["one optional field was empty"],
        )

        with patch(
            "Modules.data.data_loader.parser.parse_products_file",
            return_value=(parsed_products, summary),
            create=True,
        ):
            result = self.loader.load_products("products.csv", mode="append")

        self.assertEqual(result.accepted_count, 3)
        self.assertEqual(result.rejected_count, 1)
        self.assertEqual(result.total_processed, 4)
        self.assertEqual(result.warnings, ["one optional field was empty"])
        self.assertTrue(result.success)

    def test_parsing_failure_returns_explicit_error_result(self) -> None:
        with patch(
            "Modules.data.data_loader.parser.parse_products_file",
            side_effect=ValueError("bad source data"),
            create=True,
        ):
            result = self.loader.load_products("broken.csv", mode="append")

        self.assertEqual(result.accepted_count, 0)
        self.assertEqual(result.rejected_count, 0)
        self.assertFalse(result.success)
        self.assertTrue(any("bad source data" in message for message in result.errors))


if __name__ == "__main__":
    unittest.main()
