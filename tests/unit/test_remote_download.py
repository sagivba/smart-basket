"""Unit tests for remote transparency downloader wrapper."""

from __future__ import annotations

import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from Modules.data.remote_download import (
    DownloadBatchResult,
    RetailChainsDownloadManager,
    download_all_supported_chains,
)


class _FakeScarpingTask:
    def __init__(self, behavior: dict[tuple[str, str], str], **kwargs):
        self._behavior = behavior
        self.kwargs = kwargs

    def start(self, limit=None, when_date=None, single_pass=True):
        _ = (limit, when_date, single_pass)

    def join(self):
        chain_name = self.kwargs["enabled_scrapers"][0]
        file_type = self.kwargs["files_types"][0]
        action = self._behavior.get((chain_name, file_type), "success")
        if action.startswith("error:"):
            raise RuntimeError(action.split(":", 1)[1])
        if action == "empty":
            return

        base = Path(self.kwargs["output_configuration"]["base_storage_path"])
        file_name = f"{chain_name}_{file_type}.xml"
        (base / file_name).write_text("ok", encoding="utf-8")


def _patch_imports(behavior: dict[tuple[str, str], str]):
    fake_scraper_factory = types.SimpleNamespace(SHUFERSAL="SHUFERSAL", HAZI_HINAM="HAZI_HINAM")
    fake_file_types = types.SimpleNamespace(
        STORE_FILE="STORE_FILE",
        PRICE_FILE="PRICE_FILE",
        PRICE_FULL_FILE="PRICE_FULL_FILE",
        PROMO_FILE="PROMO_FILE",
        PROMO_FULL_FILE="PROMO_FULL_FILE",
    )

    def fake_import(name: str):
        if name == "il_supermarket_scarper":
            return types.SimpleNamespace(
                ScarpingTask=lambda **kwargs: _FakeScarpingTask(behavior=behavior, **kwargs)
            )
        if name == "il_supermarket_scarper.scrappers_factory":
            return types.SimpleNamespace(ScraperFactory=fake_scraper_factory)
        if name == "il_supermarket_scarper.utils.file_types":
            return types.SimpleNamespace(FileTypesFilters=fake_file_types)
        raise ImportError(name)

    return patch("Modules.data.remote_download.importlib.import_module", side_effect=fake_import)


class TestRetailChainsDownloadManager(unittest.TestCase):
    def test_success_flow_for_one_chain(self) -> None:
        manager = RetailChainsDownloadManager()
        with tempfile.TemporaryDirectory() as temp_dir, _patch_imports({}):
            result = manager.download_chains(target_root=temp_dir, chains=["SHUFERSAL"])

        self.assertIsInstance(result, DownloadBatchResult)
        self.assertEqual(result.requested_chains, ["SHUFERSAL"])
        self.assertTrue(result.success)
        self.assertEqual(result.total_failed_attempts, 0)
        self.assertEqual(len(result.chain_results), 1)
        self.assertTrue(all(attempt.success for attempt in result.chain_results[0].attempts))

    def test_success_flow_for_both_supported_chains(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, _patch_imports({}):
            result = download_all_supported_chains(target_root=temp_dir)

        self.assertEqual(result.requested_chains, ["SHUFERSAL", "HAZI_HINAM"])
        self.assertTrue(result.success)
        self.assertEqual(len(result.chain_results), 2)
        self.assertEqual(result.total_successful_attempts, 10)

    def test_partial_failure_flow_some_file_types_fail(self) -> None:
        manager = RetailChainsDownloadManager()
        behavior = {
            ("SHUFERSAL", "PROMO_FULL_FILE"): "empty",
            ("SHUFERSAL", "PROMO_FILE"): "error:upstream timeout",
        }
        with tempfile.TemporaryDirectory() as temp_dir, _patch_imports(behavior):
            result = manager.download_chains(target_root=temp_dir, chains=["SHUFERSAL"])

        self.assertFalse(result.success)
        self.assertEqual(result.total_failed_attempts, 2)
        attempts = result.chain_results[0].attempts
        failed = [attempt for attempt in attempts if not attempt.success]
        self.assertEqual(len(failed), 2)
        self.assertTrue(any("no files returned by upstream scraper" in (a.failure_reason or "") for a in failed))
        self.assertTrue(any("upstream timeout" in (a.failure_reason or "") for a in failed))

    def test_total_failure_flow_for_one_chain(self) -> None:
        manager = RetailChainsDownloadManager()
        behavior = {
            ("HAZI_HINAM", "STORE_FILE"): "error:boom",
            ("HAZI_HINAM", "PRICE_FILE"): "error:boom",
            ("HAZI_HINAM", "PRICE_FULL_FILE"): "error:boom",
            ("HAZI_HINAM", "PROMO_FILE"): "error:boom",
            ("HAZI_HINAM", "PROMO_FULL_FILE"): "error:boom",
        }
        with tempfile.TemporaryDirectory() as temp_dir, _patch_imports(behavior):
            result = manager.download_chains(target_root=temp_dir, chains=["HAZI_HINAM"])

        chain_result = result.chain_results[0]
        self.assertFalse(result.success)
        self.assertFalse(chain_result.success)
        self.assertEqual(result.total_successful_attempts, 0)
        self.assertEqual(result.total_failed_attempts, 5)
        self.assertTrue(chain_result.warnings)

    def test_report_rendering_content(self) -> None:
        manager = RetailChainsDownloadManager()
        behavior = {("HAZI_HINAM", "PROMO_FULL_FILE"): "empty"}
        with tempfile.TemporaryDirectory() as temp_dir, _patch_imports(behavior):
            result = manager.download_chains(target_root=temp_dir, chains=["HAZI_HINAM"])
            report = manager.render_report(result)

        self.assertIn("Download batch summary", report)
        self.assertIn("HAZI_HINAM | PROMO_FULL_FILE | FAILED", report)
        self.assertIn("no files returned by upstream scraper", report)
        self.assertIn("HAZI_HINAM | STORE_FILE | SUCCESS", report)

    def test_deterministic_folder_layout(self) -> None:
        manager = RetailChainsDownloadManager()
        with tempfile.TemporaryDirectory() as temp_dir, _patch_imports({}):
            result = manager.download_chains(target_root=temp_dir)
            shufersal_dir = Path(temp_dir) / "shufersal"
            hazi_hinam_dir = Path(temp_dir) / "hazi_hinam"
            self.assertTrue(shufersal_dir.exists())
            self.assertTrue(hazi_hinam_dir.exists())
            all_paths = [path for chain in result.chain_results for path in chain.downloaded_files]
            self.assertTrue(all(str(path).startswith(str(shufersal_dir)) or str(path).startswith(str(hazi_hinam_dir)) for path in all_paths))


if __name__ == "__main__":
    unittest.main()
