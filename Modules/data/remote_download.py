"""Remote transparency-file download integration via il-supermarket-scraper."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
import importlib
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class DownloadJob:
    """Describes one deterministic remote-download operation for one chain."""

    chain: str
    target_directory: Path
    selected_file_types: list[str]
    when_date: date | datetime | None = None
    limit: int | None = None


@dataclass(slots=True)
class DownloadedFile:
    """Represents one file downloaded to local storage."""

    chain: str
    file_type: str
    file_name: str
    file_path: Path


@dataclass(slots=True)
class DownloadResult:
    """Structured aggregate output from one downloader run."""

    requested_chains: list[str]
    selected_file_types: list[str]
    target_root: Path
    downloaded_files: list[DownloadedFile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Return True when no chain-level errors were recorded."""
        return not self.errors


class RetailerTransparencyDownloader:
    """Downloads raw transparency files for supported chains only."""

    def download_files(
        self,
        target_root: str | Path = "data/raw/downloads",
        when_date: date | datetime | None = None,
        limit: int | None = None,
        include_store_files: bool = True,
        prefer_full_price_files: bool = True,
    ) -> DownloadResult:
        """Download raw files for SHUFERSAL and HAZI_HINAM using upstream package."""
        resolved_target_root = Path(target_root)

        try:
            package_api = self._load_package_api()
        except Exception as exc:
            return DownloadResult(
                requested_chains=["SHUFERSAL", "HAZI_HINAM"],
                selected_file_types=[],
                target_root=resolved_target_root,
                errors=[f"failed to load il-supermarket-scraper API: {exc}"],
            )

        supported_chains = self._resolve_supported_chains(package_api)
        selected_file_types = self._select_file_types(
            package_api=package_api,
            include_store_files=include_store_files,
            prefer_full_price_files=prefer_full_price_files,
        )
        result = DownloadResult(
            requested_chains=supported_chains,
            selected_file_types=selected_file_types,
            target_root=resolved_target_root,
        )

        for chain_name in supported_chains:
            chain_target = self._default_chain_target(resolved_target_root, chain_name)
            job = DownloadJob(
                chain=chain_name,
                target_directory=chain_target,
                selected_file_types=list(selected_file_types),
                when_date=when_date,
                limit=limit,
            )
            try:
                job.target_directory.mkdir(parents=True, exist_ok=True)
                task = package_api["ScarpingTask"](
                    enabled_scrapers=[job.chain],
                    files_types=list(job.selected_file_types),
                    multiprocessing=1,
                    output_configuration={
                        "output_mode": "disk",
                        "base_storage_path": str(job.target_directory),
                    },
                )
                task.start(limit=job.limit, when_date=job.when_date, single_pass=True)
                task.join()
            except Exception as exc:
                result.errors.append(f"{job.chain}: download failed: {exc}")
                continue

            result.downloaded_files.extend(
                self._collect_downloaded_files(chain_name=job.chain, target_directory=job.target_directory)
            )
            if prefer_full_price_files and not any(
                file.chain == job.chain and file.file_type == "PRICE_FULL_FILE"
                for file in result.downloaded_files
            ):
                result.warnings.append(
                    f"{job.chain}: PRICE_FULL_FILE not found; fallback PRICE_FILE was allowed"
                )

        return result

    @staticmethod
    def _load_package_api() -> dict[str, Any]:
        package = importlib.import_module("il_supermarket_scarper")
        scraper_factory_module = importlib.import_module("il_supermarket_scarper.scrappers_factory")
        file_types_module = importlib.import_module("il_supermarket_scarper.utils.file_types")
        return {
            "ScarpingTask": getattr(package, "ScarpingTask"),
            "ScraperFactory": getattr(scraper_factory_module, "ScraperFactory"),
            "FileTypesFilters": getattr(file_types_module, "FileTypesFilters"),
        }

    @staticmethod
    def _resolve_supported_chains(package_api: dict[str, Any]) -> list[str]:
        scraper_factory = package_api["ScraperFactory"]
        return [
            getattr(scraper_factory, "SHUFERSAL"),
            getattr(scraper_factory, "HAZI_HINAM"),
        ]

    @staticmethod
    def _default_chain_target(target_root: Path, chain_name: str) -> Path:
        slug = "shufersal" if chain_name == "SHUFERSAL" else "hazi_hinam"
        return target_root / slug

    @staticmethod
    def _select_file_types(
        *,
        package_api: dict[str, Any],
        include_store_files: bool,
        prefer_full_price_files: bool,
    ) -> list[str]:
        file_types = package_api["FileTypesFilters"]
        selected: list[str] = []
        if include_store_files:
            selected.append(getattr(file_types, "STORE_FILE"))
        if prefer_full_price_files:
            selected.extend(
                [
                    getattr(file_types, "PRICE_FULL_FILE"),
                    getattr(file_types, "PRICE_FILE"),
                ]
            )
        else:
            selected.append(getattr(file_types, "PRICE_FILE"))
        return selected

    def _collect_downloaded_files(
        self,
        *,
        chain_name: str,
        target_directory: Path,
    ) -> list[DownloadedFile]:
        if not target_directory.exists():
            return []

        downloaded_files: list[DownloadedFile] = []
        for file_path in sorted(path for path in target_directory.rglob("*") if path.is_file()):
            downloaded_files.append(
                DownloadedFile(
                    chain=chain_name,
                    file_type=self._detect_file_type(file_path.name),
                    file_name=file_path.name,
                    file_path=file_path,
                )
            )
        return downloaded_files

    @staticmethod
    def _detect_file_type(file_name: str) -> str:
        lowered = file_name.lower()
        if "pricefull" in lowered:
            return "PRICE_FULL_FILE"
        if "price" in lowered:
            return "PRICE_FILE"
        if "store" in lowered:
            return "STORE_FILE"
        return "UNKNOWN"
