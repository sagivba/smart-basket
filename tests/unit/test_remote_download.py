"""Unit tests for remote transparency downloader wrapper."""

from __future__ import annotations

import tempfile
import types
import unittest
from enum import Enum
from pathlib import Path
from unittest.mock import patch

from Modules.data.remote_download import (
    AttemptStatus,
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


class _ExplodingPath:
    def mkdir(self, parents=True, exist_ok=True):
        _ = (parents, exist_ok)
        raise RuntimeError("missing dependency: il_supermarket_scarper")


class _FakeScraperFactoryEnum(Enum):
    SHUFERSAL = "SHUFERSAL"
    HAZI_HINAM = "HAZI_HINAM"


class _FakeFileTypesEnum(Enum):
    STORE_FILE = "STORE_FILE"
    PRICE_FILE = "PRICE_FILE"
    PRICE_FULL_FILE = "PRICE_FULL_FILE"
    PROMO_FILE = "PROMO_FILE"
    PROMO_FULL_FILE = "PROMO_FULL_FILE"


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


def _patch_imports_with_enums(
    behavior: dict[tuple[str, str], str],
    *,
    fail_on_enum_input: bool = False,
    thread_error: Exception | None = None,
):
    class _EnumAwareTask:
        def __init__(self, behavior: dict[tuple[str, str], str], **kwargs):
            self._behavior = behavior
            self.kwargs = kwargs
            self.thread_exceptions = [thread_error] if thread_error is not None else []
            scraper = kwargs["enabled_scrapers"][0]
            file_type = kwargs["files_types"][0]
            if fail_on_enum_input and (isinstance(scraper, Enum) or isinstance(file_type, Enum)):
                raise KeyError(scraper)

        def start(self, limit=None, when_date=None, single_pass=True):
            _ = (limit, when_date, single_pass)

        def join(self):
            if self.thread_exceptions:
                return
            chain_name = self.kwargs["enabled_scrapers"][0]
            file_type = self.kwargs["files_types"][0]
            chain_key = chain_name if isinstance(chain_name, str) else chain_name.name
            file_type_key = file_type if isinstance(file_type, str) else file_type.name
            action = self._behavior.get((chain_key, file_type_key), "success")
            if action == "empty":
                return
            base = Path(self.kwargs["output_configuration"]["base_storage_path"])
            (base / f"{chain_key}_{file_type_key}.xml").write_text("ok", encoding="utf-8")

    def fake_import(name: str):
        if name == "il_supermarket_scarper":
            return types.SimpleNamespace(
                ScarpingTask=lambda **kwargs: _EnumAwareTask(behavior=behavior, **kwargs)
            )
        if name == "il_supermarket_scarper.scrappers_factory":
            return types.SimpleNamespace(ScraperFactory=_FakeScraperFactoryEnum)
        if name == "il_supermarket_scarper.utils.file_types":
            return types.SimpleNamespace(FileTypesFilters=_FakeFileTypesEnum)
        raise ImportError(name)

    return patch("Modules.data.remote_download.importlib.import_module", side_effect=fake_import)


class TestRetailChainsDownloadManager(unittest.TestCase):
    def test_resolve_requested_chains_normalizes_enum_inputs_to_strings(self) -> None:
        manager = RetailChainsDownloadManager()
        package_api = {"ScraperFactory": _FakeScraperFactoryEnum}
        resolved = manager._resolve_requested_chains(
            package_api=package_api,
            requested_chains=[_FakeScraperFactoryEnum.SHUFERSAL, "hazi_hinam"],
        )
        self.assertEqual(resolved, ["SHUFERSAL", "HAZI_HINAM"])

    def test_upstream_receives_strings_not_enum_members(self) -> None:
        manager = RetailChainsDownloadManager()
        with tempfile.TemporaryDirectory() as temp_dir, _patch_imports_with_enums({}, fail_on_enum_input=True):
            result = manager.download_chains(
                target_root=temp_dir,
                chains=[_FakeScraperFactoryEnum.SHUFERSAL],
                file_types=[_FakeFileTypesEnum.STORE_FILE],
            )

        self.assertTrue(result.success)
        self.assertEqual(result.requested_chains, ["SHUFERSAL"])
        self.assertEqual(result.chain_results[0].attempts[0].chain_name, "SHUFERSAL")
        self.assertEqual(result.chain_results[0].attempts[0].file_type, "STORE_FILE")

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
        self.assertEqual(result.total_skipped_attempts, 0)
        attempts = result.chain_results[0].attempts
        failed = [attempt for attempt in attempts if not attempt.success]
        self.assertEqual(len(failed), 2)
        self.assertTrue(any("no files returned by upstream scraper" in (a.failure_reason or "") for a in failed))
        self.assertTrue(any("upstream timeout" in (a.failure_reason or "") for a in failed))
        self.assertTrue(all(a.failure_detail is not None for a in failed))
        timeout_attempt = next(a for a in failed if "upstream timeout" in (a.failure_reason or ""))
        self.assertEqual(timeout_attempt.failure_detail.exception_class_name, "RuntimeError")
        self.assertEqual(timeout_attempt.failure_detail.exception_message, "upstream timeout")

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
        self.assertTrue(all(a.status == AttemptStatus.FAILED for a in chain_result.attempts))

    def test_report_rendering_content(self) -> None:
        manager = RetailChainsDownloadManager()
        behavior = {("HAZI_HINAM", "PROMO_FULL_FILE"): "empty"}
        with tempfile.TemporaryDirectory() as temp_dir, _patch_imports(behavior):
            result = manager.download_chains(target_root=temp_dir, chains=["HAZI_HINAM"])
            report = manager.render_report(result)

        self.assertIn("Download batch summary", report)
        self.assertIn("Chain: HAZI_HINAM", report)
        self.assertIn("- PROMO_FULL_FILE: FAILED | reason=no files returned by upstream scraper", report)
        self.assertIn("- STORE_FILE: SUCCESS | paths=", report)

    def test_render_report_never_crashes_with_unexpected_values(self) -> None:
        manager = RetailChainsDownloadManager()
        batch_result = DownloadBatchResult(
            requested_chains=[_FakeScraperFactoryEnum.SHUFERSAL],
            root_target_directory=Path("/tmp/any"),
            started_at=None,  # type: ignore[arg-type]
            finished_at=None,  # type: ignore[arg-type]
            chain_results=[],
            success=False,
        )
        report = manager.render_report(batch_result)
        self.assertIsInstance(report, str)
        self.assertIn("chains=SHUFERSAL", report)

    def test_render_report_two_chains_partial_failure_with_separate_reasons(self) -> None:
        manager = RetailChainsDownloadManager()
        behavior = {
            ("SHUFERSAL", "PRICE_FILE"): "error:timeout while downloading",
            ("HAZI_HINAM", "STORE_FILE"): "empty",
        }
        with tempfile.TemporaryDirectory() as temp_dir, _patch_imports(behavior):
            result = manager.download_chains(
                target_root=temp_dir,
                chains=["SHUFERSAL", "HAZI_HINAM"],
                file_types=["STORE_FILE", "PRICE_FILE"],
            )
            report = manager.render_report(result)

        self.assertEqual(result.total_successful_attempts, 2)
        self.assertEqual(result.total_failed_attempts, 2)
        self.assertIn("Chain: SHUFERSAL", report)
        self.assertIn("- PRICE_FILE: FAILED | reason=runtimeerror: timeout while downloading", report)
        self.assertIn("Chain: HAZI_HINAM", report)
        self.assertIn("- STORE_FILE: FAILED | reason=no files returned by upstream scraper", report)

    def test_chain_init_exception_is_rendered_and_file_types_marked_skipped(self) -> None:
        manager = RetailChainsDownloadManager()
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(manager, "_default_chain_target", return_value=_ExplodingPath()):
                with _patch_imports({}):
                    result = manager.download_chains(
                        target_root=temp_dir,
                        chains=["SHUFERSAL"],
                        file_types=["STORE_FILE", "PRICE_FILE"],
                    )
                    report = manager.render_report(result)

        self.assertFalse(result.success)
        self.assertEqual(result.total_failed_attempts, 1)
        self.assertEqual(result.total_skipped_attempts, 2)
        self.assertIn("- CHAIN_INIT: FAILED | reason=runtimeerror: missing dependency: il_supermarket_scarper", report)
        self.assertIn("- STORE_FILE: SKIPPED | reason=chain initialization failed: runtimeerror: missing dependency: il_supermarket_scarper", report)
        self.assertIn("- PRICE_FILE: SKIPPED | reason=chain initialization failed: runtimeerror: missing dependency: il_supermarket_scarper", report)

    def test_invalid_scraper_identifier_is_normalized(self) -> None:
        manager = RetailChainsDownloadManager()

        class _BadTask:
            def __init__(self, **kwargs):
                _ = kwargs
                raise KeyError("<ScraperFactory.SHUFERSAL>")

        package_api = {
            "ScarpingTask": _BadTask,
            "ScraperFactory": _FakeScraperFactoryEnum,
            "FileTypesFilters": _FakeFileTypesEnum,
        }
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            manager,
            "_load_package_api",
            return_value=package_api,
        ):
            result = manager.download_chains(
                target_root=temp_dir,
                chains=["SHUFERSAL"],
                file_types=["STORE_FILE"],
            )

        self.assertFalse(result.success)
        self.assertIn("invalid scraper identifier passed to upstream package", result.chain_results[0].errors[0])
        self.assertEqual(
            result.chain_results[0].attempts[0].failure_detail.exception_class_name,
            "KeyError",
        )

    def test_background_thread_errors_are_captured_as_failures(self) -> None:
        manager = RetailChainsDownloadManager()
        with tempfile.TemporaryDirectory() as temp_dir, _patch_imports_with_enums(
            {},
            thread_error=RuntimeError("thread timeout"),
        ):
            result = manager.download_chains(
                target_root=temp_dir,
                chains=["SHUFERSAL"],
                file_types=["STORE_FILE"],
            )

        self.assertFalse(result.success)
        self.assertEqual(result.total_failed_attempts, 1)
        self.assertIn("thread timeout", result.chain_results[0].attempts[0].failure_reason)

    def test_join_over_requested_chains_never_crashes(self) -> None:
        manager = RetailChainsDownloadManager()
        with tempfile.TemporaryDirectory() as temp_dir, _patch_imports_with_enums({}, fail_on_enum_input=True):
            result = manager.download_chains(
                target_root=temp_dir,
                chains=[_FakeScraperFactoryEnum.SHUFERSAL],
                file_types=["STORE_FILE"],
            )
            report = manager.render_report(result)
        self.assertIn("chains=SHUFERSAL", report)

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
