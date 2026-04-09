"""Unit tests for remote transparency downloader integration."""

from __future__ import annotations

import tempfile
import types
import unittest
from unittest.mock import patch

from Modules.data.remote_download import DownloadResult, RetailerTransparencyDownloader


class TestRetailerTransparencyDownloader(unittest.TestCase):
    def test_download_requests_only_supported_chains_and_file_types(self) -> None:
        created_tasks: list[object] = []

        class FakeScarpingTask:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                created_tasks.append(self)

            def start(self, limit=None, when_date=None, single_pass=True):
                _ = (limit, when_date, single_pass)

            def join(self):
                base_storage_path = self.kwargs["output_configuration"]["base_storage_path"]
                chain_name = self.kwargs["enabled_scrapers"][0]
                with open(f"{base_storage_path}/{chain_name}_Store.xml", "w", encoding="utf-8") as handle:
                    handle.write("store")
                with open(f"{base_storage_path}/{chain_name}_PriceFull.xml", "w", encoding="utf-8") as handle:
                    handle.write("price-full")

        fake_scraper_factory = types.SimpleNamespace(
            SHUFERSAL="SHUFERSAL",
            HAZI_HINAM="HAZI_HINAM",
        )
        fake_file_types = types.SimpleNamespace(
            STORE_FILE="STORE_FILE",
            PRICE_FULL_FILE="PRICE_FULL_FILE",
            PRICE_FILE="PRICE_FILE",
            PROMO_FILE="PROMO_FILE",
        )

        def fake_import(name: str):
            if name == "il_supermarket_scarper":
                return types.SimpleNamespace(ScarpingTask=FakeScarpingTask)
            if name == "il_supermarket_scarper.scrappers_factory":
                return types.SimpleNamespace(ScraperFactory=fake_scraper_factory)
            if name == "il_supermarket_scarper.utils.file_types":
                return types.SimpleNamespace(FileTypesFilters=fake_file_types)
            raise ImportError(name)

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "Modules.data.remote_download.importlib.import_module",
            side_effect=fake_import,
        ):
            result = RetailerTransparencyDownloader().download_files(target_root=temp_dir)

        self.assertEqual(result.requested_chains, ["SHUFERSAL", "HAZI_HINAM"])
        self.assertEqual(result.selected_file_types, ["STORE_FILE", "PRICE_FULL_FILE", "PRICE_FILE"])
        self.assertTrue(result.success)
        self.assertEqual(len(created_tasks), 2)
        self.assertEqual(created_tasks[0].kwargs["enabled_scrapers"], ["SHUFERSAL"])
        self.assertEqual(created_tasks[1].kwargs["enabled_scrapers"], ["HAZI_HINAM"])
        for task in created_tasks:
            self.assertIn("STORE_FILE", task.kwargs["files_types"])
            self.assertIn("PRICE_FULL_FILE", task.kwargs["files_types"])
            self.assertIn("PRICE_FILE", task.kwargs["files_types"])
            self.assertNotIn("PROMO_FILE", task.kwargs["files_types"])

    def test_download_result_contains_structured_downloaded_files(self) -> None:
        class FakeScarpingTask:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def start(self, limit=None, when_date=None, single_pass=True):
                _ = (limit, when_date, single_pass)

            def join(self):
                base_storage_path = self.kwargs["output_configuration"]["base_storage_path"]
                chain_name = self.kwargs["enabled_scrapers"][0]
                with open(f"{base_storage_path}/{chain_name}_Store.xml", "w", encoding="utf-8") as handle:
                    handle.write("store")
                with open(f"{base_storage_path}/{chain_name}_Price.xml", "w", encoding="utf-8") as handle:
                    handle.write("price")

        fake_scraper_factory = types.SimpleNamespace(SHUFERSAL="SHUFERSAL", HAZI_HINAM="HAZI_HINAM")
        fake_file_types = types.SimpleNamespace(
            STORE_FILE="STORE_FILE",
            PRICE_FULL_FILE="PRICE_FULL_FILE",
            PRICE_FILE="PRICE_FILE",
        )

        def fake_import(name: str):
            mapping = {
                "il_supermarket_scarper": types.SimpleNamespace(ScarpingTask=FakeScarpingTask),
                "il_supermarket_scarper.scrappers_factory": types.SimpleNamespace(
                    ScraperFactory=fake_scraper_factory
                ),
                "il_supermarket_scarper.utils.file_types": types.SimpleNamespace(
                    FileTypesFilters=fake_file_types
                ),
            }
            return mapping[name]

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "Modules.data.remote_download.importlib.import_module",
            side_effect=fake_import,
        ):
            result = RetailerTransparencyDownloader().download_files(target_root=temp_dir)

        self.assertIsInstance(result, DownloadResult)
        self.assertTrue(str(result.target_root))
        self.assertGreaterEqual(len(result.downloaded_files), 4)
        self.assertTrue(any(file.file_type == "STORE_FILE" for file in result.downloaded_files))
        self.assertTrue(any(file.file_type == "PRICE_FILE" for file in result.downloaded_files))
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 2)

    def test_download_failures_are_reported_as_structured_errors(self) -> None:
        class FakeScarpingTask:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def start(self, limit=None, when_date=None, single_pass=True):
                chain_name = self.kwargs["enabled_scrapers"][0]
                if chain_name == "HAZI_HINAM":
                    raise RuntimeError("boom")

            def join(self):
                base_storage_path = self.kwargs["output_configuration"]["base_storage_path"]
                chain_name = self.kwargs["enabled_scrapers"][0]
                with open(f"{base_storage_path}/{chain_name}_Store.xml", "w", encoding="utf-8") as handle:
                    handle.write("store")

        fake_scraper_factory = types.SimpleNamespace(SHUFERSAL="SHUFERSAL", HAZI_HINAM="HAZI_HINAM")
        fake_file_types = types.SimpleNamespace(
            STORE_FILE="STORE_FILE",
            PRICE_FULL_FILE="PRICE_FULL_FILE",
            PRICE_FILE="PRICE_FILE",
        )

        def fake_import(name: str):
            mapping = {
                "il_supermarket_scarper": types.SimpleNamespace(ScarpingTask=FakeScarpingTask),
                "il_supermarket_scarper.scrappers_factory": types.SimpleNamespace(
                    ScraperFactory=fake_scraper_factory
                ),
                "il_supermarket_scarper.utils.file_types": types.SimpleNamespace(
                    FileTypesFilters=fake_file_types
                ),
            }
            return mapping[name]

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "Modules.data.remote_download.importlib.import_module",
            side_effect=fake_import,
        ):
            result = RetailerTransparencyDownloader().download_files(target_root=temp_dir)

        self.assertFalse(result.success)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("HAZI_HINAM", result.errors[0])
        self.assertTrue(any(file.chain == "SHUFERSAL" for file in result.downloaded_files))


if __name__ == "__main__":
    unittest.main()
