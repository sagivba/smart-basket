"""Unit tests for the basic CLI entry point."""

from __future__ import annotations

import io
import sqlite3
import tempfile
import unittest
from pathlib import Path

from Modules.app.cli import run_cli
from Modules.db.database import create_schema


class TestCli(unittest.TestCase):
    def test_load_command_loads_products_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "cli.sqlite"
            fixture_path = Path("tests/fixtures/parser/products_valid.csv")
            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = run_cli(
                [
                    "--db-path",
                    str(db_path),
                    "load",
                    "products",
                    str(fixture_path),
                    "--mode",
                    "append",
                ],
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("Loaded products: accepted=2, rejected=0", stdout.getvalue())

    def test_add_item_command_matches_barcode_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "cli.sqlite"
            connection = sqlite3.connect(db_path)
            create_schema(connection)
            connection.execute(
                """
                INSERT INTO products (barcode, name, normalized_name, brand, unit_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("12345", "Milk 1L", "milk 1l", None, None),
            )
            connection.commit()
            connection.close()

            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = run_cli(
                [
                    "--db-path",
                    str(db_path),
                    "add-item",
                    "100",
                    "12345",
                    "--input-type",
                    "barcode",
                    "--quantity",
                    "2",
                ],
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("status=matched", stdout.getvalue())


    def test_add_item_name_command_marks_unmatched_when_product_name_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "cli.sqlite"
            connection = sqlite3.connect(db_path)
            create_schema(connection)
            connection.commit()
            connection.close()

            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = run_cli(
                [
                    "--db-path",
                    str(db_path),
                    "add-item",
                    "100",
                    "Unknown Product",
                    "--input-type",
                    "name",
                    "--quantity",
                    "1",
                ],
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("status=unmatched", stdout.getvalue())

    def test_add_item_name_command_matches_normalized_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "cli.sqlite"
            connection = sqlite3.connect(db_path)
            create_schema(connection)
            connection.execute(
                """
                INSERT INTO products (barcode, name, normalized_name, brand, unit_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("12345", "Milk 1L", "milk 1l", None, None),
            )
            connection.commit()
            connection.close()

            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = run_cli(
                [
                    "--db-path",
                    str(db_path),
                    "add-item",
                    "100",
                    "  MILK 1L  ",
                    "--input-type",
                    "name",
                    "--quantity",
                    "1",
                ],
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("status=matched", stdout.getvalue())

    def test_add_item_name_command_marks_ambiguous_without_auto_selecting_product(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "cli.sqlite"
            connection = sqlite3.connect(db_path)
            create_schema(connection)
            connection.execute(
                """
                INSERT INTO products (barcode, name, normalized_name, brand, unit_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("11111", "Milk 1L", "milk", None, None),
            )
            connection.execute(
                """
                INSERT INTO products (barcode, name, normalized_name, brand, unit_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("22222", "Milk 3%", "milk", None, None),
            )
            connection.commit()
            connection.close()

            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = run_cli(
                [
                    "--db-path",
                    str(db_path),
                    "add-item",
                    "100",
                    "Milk",
                    "--input-type",
                    "name",
                    "--quantity",
                    "1",
                ],
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("status=ambiguous", stdout.getvalue())

            persisted_connection = sqlite3.connect(db_path)
            persisted_row = persisted_connection.execute(
                """
                SELECT product_id, match_status
                FROM basket_items
                WHERE basket_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (100,),
            ).fetchone()
            persisted_connection.close()

            self.assertIsNotNone(persisted_row)
            self.assertIsNone(persisted_row[0])
            self.assertEqual(persisted_row[1], "ambiguous")

    def test_compare_command_prints_ranked_results_missing_and_unmatched(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "cli.sqlite"
            connection = sqlite3.connect(db_path)
            create_schema(connection)

            connection.execute(
                "INSERT INTO products (id, barcode, name, normalized_name, brand, unit_name) VALUES (1, '111', 'Milk', 'milk', NULL, NULL)"
            )
            connection.execute(
                "INSERT INTO products (id, barcode, name, normalized_name, brand, unit_name) VALUES (2, '222', 'Eggs', 'eggs', NULL, NULL)"
            )
            connection.execute("INSERT INTO chains (id, chain_code, name) VALUES (10, 'A', 'Alpha')")
            connection.execute("INSERT INTO chains (id, chain_code, name) VALUES (20, 'B', 'Beta')")
            connection.execute(
                "INSERT INTO stores (id, chain_id, store_code, name, city, address, is_active) VALUES (100, 10, 'S1', 'Alpha Main', NULL, NULL, 1)"
            )
            connection.execute(
                "INSERT INTO stores (id, chain_id, store_code, name, city, address, is_active) VALUES (200, 20, 'S2', 'Beta Main', NULL, NULL, 1)"
            )

            connection.execute(
                "INSERT INTO prices (product_id, chain_id, store_id, price, currency, price_date, source_file) VALUES (1, 10, 100, 5.0, 'ILS', '2026-04-01', 'fixture')"
            )
            connection.execute(
                "INSERT INTO prices (product_id, chain_id, store_id, price, currency, price_date, source_file) VALUES (2, 10, 100, 7.0, 'ILS', '2026-04-01', 'fixture')"
            )
            connection.execute(
                "INSERT INTO prices (product_id, chain_id, store_id, price, currency, price_date, source_file) VALUES (1, 20, 200, 4.5, 'ILS', '2026-04-01', 'fixture')"
            )

            connection.execute(
                "INSERT INTO basket_items (basket_id, product_id, input_value, input_type, quantity, match_status) VALUES (1, 1, '111', 'barcode', 1, 'matched')"
            )
            connection.execute(
                "INSERT INTO basket_items (basket_id, product_id, input_value, input_type, quantity, match_status) VALUES (1, 2, '222', 'barcode', 1, 'matched')"
            )
            connection.execute(
                "INSERT INTO basket_items (basket_id, product_id, input_value, input_type, quantity, match_status) VALUES (1, NULL, 'mystery', 'name', 1, 'unmatched')"
            )
            connection.commit()
            connection.close()

            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = run_cli(
                ["--db-path", str(db_path), "compare", "1"],
                stdout=stdout,
                stderr=stderr,
            )

            output = stdout.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("1. Alpha | total=12.00 | status=complete", output)
            self.assertIn("2. Beta | total=4.50 | status=partial", output)
            self.assertIn("Missing items: Eggs", output)
            self.assertIn("Unmatched items: mystery", output)

    def test_load_command_returns_friendly_error_for_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "cli.sqlite"
            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = run_cli(
                [
                    "--db-path",
                    str(db_path),
                    "load",
                    "products",
                    "tests/fixtures/parser/does_not_exist.csv",
                ],
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("Load failed for products", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
