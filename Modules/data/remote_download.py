"""Remote transparency-file download integration via il-supermarket-scraper."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from datetime import date, datetime
import importlib
from pathlib import Path
from typing import Any


SUPPORTED_CHAIN_ORDER = ("SHUFERSAL", "HAZI_HINAM")
DEFAULT_FILE_TYPE_ORDER = (
    "STORE_FILE",
    "PRICE_FILE",
    "PRICE_FULL_FILE",
    "PROMO_FILE",
    "PROMO_FULL_FILE",
)


@dataclass(slots=True)
class ChainDownloadRequest:
    """Input contract for one chain-level download request."""

    chain_name: str
    file_types: list[str]
    target_directory: Path
    when_date: date | datetime | None = None
    limit: int | None = None


class AttemptStatus(str, Enum):
    """Status values for deterministic per-attempt reporting."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass(slots=True)
class FailureDetail:
    """Structured failure detail that preserves root-cause information."""

    chain_name: str
    file_type: str
    exception_class_name: str
    exception_message: str
    normalized_reason: str


@dataclass(slots=True)
class FileDownloadAttempt:
    """Result of attempting to download one file category for one chain."""

    chain_name: str
    file_type: str
    target_directory: Path
    expected_file_name: str | None
    discovered_file_name: str | None
    status: AttemptStatus
    failure_reason: str | None
    failure_detail: FailureDetail | None = None
    downloaded_file_paths: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status == AttemptStatus.SUCCESS


@dataclass(slots=True)
class ChainDownloadResult:
    """Aggregated result for one chain across requested file categories."""

    chain_name: str
    success: bool
    requested_file_types: list[str]
    attempts: list[FileDownloadAttempt] = field(default_factory=list)
    downloaded_files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DownloadBatchResult:
    """Aggregated result for one cross-chain download run."""

    requested_chains: list[str]
    root_target_directory: Path
    started_at: datetime
    finished_at: datetime
    chain_results: list[ChainDownloadResult] = field(default_factory=list)
    total_files_downloaded: int = 0
    total_successful_attempts: int = 0
    total_failed_attempts: int = 0
    total_skipped_attempts: int = 0
    success: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class RetailChainsDownloadManager:
    """Higher-level wrapper around the upstream transparency downloader API."""

    def download_chains(
        self,
        target_root: str | Path = "data/raw/downloads",
        chains: list[str] | tuple[str, ...] | None = None,
        file_types: list[str] | tuple[str, ...] | None = None,
        when_date: date | datetime | None = None,
        limit: int | None = None,
    ) -> DownloadBatchResult:
        """Download requested file categories for requested supported chains."""
        started_at = datetime.utcnow()
        resolved_root = Path(target_root)

        try:
            package_api = self._load_package_api()
        except Exception as exc:
            finished_at = datetime.utcnow()
            normalized_reason = self._normalize_failure_reason(exc)
            resolved_requested_chains = list(chains or SUPPORTED_CHAIN_ORDER)
            chain_results = [
                self._build_chain_init_failure_result(
                    chain_name=chain_name,
                    file_types=list(file_types or DEFAULT_FILE_TYPE_ORDER),
                    target_directory=self._default_chain_target(resolved_root, chain_name),
                    exc=exc,
                    normalized_reason=normalized_reason,
                )
                for chain_name in resolved_requested_chains
            ]
            return DownloadBatchResult(
                requested_chains=resolved_requested_chains,
                root_target_directory=resolved_root,
                started_at=started_at,
                finished_at=finished_at,
                chain_results=chain_results,
                total_failed_attempts=len(chain_results),
                total_skipped_attempts=sum(len(c.requested_file_types) for c in chain_results),
                success=False,
                errors=[f"failed to load il-supermarket-scraper API: {normalized_reason}"],
            )

        resolved_chains = self._resolve_requested_chains(package_api=package_api, requested_chains=chains)
        resolved_file_types = self._resolve_requested_file_types(
            package_api=package_api,
            requested_file_types=file_types,
        )

        chain_results: list[ChainDownloadResult] = []
        batch_errors: list[str] = []
        batch_warnings: list[str] = []

        for chain_name in resolved_chains:
            chain_target = self._default_chain_target(resolved_root, chain_name)
            chain_request = ChainDownloadRequest(
                chain_name=chain_name,
                file_types=list(resolved_file_types),
                target_directory=chain_target,
                when_date=when_date,
                limit=limit,
            )
            chain_result = self._download_chain(package_api=package_api, request=chain_request)
            chain_results.append(chain_result)
            batch_errors.extend(chain_result.errors)
            batch_warnings.extend(chain_result.warnings)

        finished_at = datetime.utcnow()
        total_successful_attempts = sum(
            1
            for chain_result in chain_results
            for attempt in chain_result.attempts
            if attempt.status == AttemptStatus.SUCCESS
        )
        total_failed_attempts = sum(
            1
            for chain_result in chain_results
            for attempt in chain_result.attempts
            if attempt.status == AttemptStatus.FAILED
        )
        total_skipped_attempts = sum(
            1
            for chain_result in chain_results
            for attempt in chain_result.attempts
            if attempt.status == AttemptStatus.SKIPPED
        )
        total_files_downloaded = sum(len(chain_result.downloaded_files) for chain_result in chain_results)

        return DownloadBatchResult(
            requested_chains=resolved_chains,
            root_target_directory=resolved_root,
            started_at=started_at,
            finished_at=finished_at,
            chain_results=chain_results,
            total_files_downloaded=total_files_downloaded,
            total_successful_attempts=total_successful_attempts,
            total_failed_attempts=total_failed_attempts,
            total_skipped_attempts=total_skipped_attempts,
            success=(total_failed_attempts == 0 and not batch_errors),
            warnings=batch_warnings,
            errors=batch_errors,
        )

    def render_report(self, batch_result: DownloadBatchResult) -> str:
        """Render a deterministic human-readable report for batch results."""
        lines = [
            "Download batch summary",
            f"root={batch_result.root_target_directory}",
            f"chains={','.join(batch_result.requested_chains)}",
            f"attempts_success={batch_result.total_successful_attempts}",
            f"attempts_failed={batch_result.total_failed_attempts}",
            f"attempts_skipped={batch_result.total_skipped_attempts}",
            f"files_downloaded={batch_result.total_files_downloaded}",
            f"overall_success={batch_result.success}",
        ]

        for chain_result in batch_result.chain_results:
            lines.append("")
            lines.append(f"Chain: {chain_result.chain_name}")
            for attempt in chain_result.attempts:
                line = f"- {attempt.file_type}: {attempt.status.value}"
                if attempt.status == AttemptStatus.SUCCESS:
                    path_text = ", ".join(str(path) for path in attempt.downloaded_file_paths) or "none"
                    line += f" | paths={path_text}"
                else:
                    reason = attempt.failure_reason or "unknown failure"
                    line += f" | reason={reason}"
                if attempt.warnings:
                    line += f" | warnings={'; '.join(attempt.warnings)}"
                lines.append(line)
            for warning in chain_result.warnings:
                lines.append(f"- WARNING: {warning}")
        return "\n".join(lines)

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
    def _resolve_requested_chains(
        *,
        package_api: dict[str, Any],
        requested_chains: list[str] | tuple[str, ...] | None,
    ) -> list[str]:
        scraper_factory = package_api["ScraperFactory"]
        supported = {
            "SHUFERSAL": getattr(scraper_factory, "SHUFERSAL"),
            "HAZI_HINAM": getattr(scraper_factory, "HAZI_HINAM"),
        }
        chain_names = list(requested_chains) if requested_chains is not None else list(SUPPORTED_CHAIN_ORDER)
        resolved: list[str] = []
        for chain_name in chain_names:
            canonical = str(chain_name).upper()
            if canonical in supported:
                resolved.append(supported[canonical])
        return resolved

    @staticmethod
    def _resolve_requested_file_types(
        *,
        package_api: dict[str, Any],
        requested_file_types: list[str] | tuple[str, ...] | None,
    ) -> list[str]:
        file_types = package_api["FileTypesFilters"]
        source_types = (
            list(requested_file_types)
            if requested_file_types is not None
            else list(DEFAULT_FILE_TYPE_ORDER)
        )
        resolved: list[str] = []
        for file_type_name in source_types:
            upper_name = str(file_type_name).upper()
            if hasattr(file_types, upper_name):
                resolved.append(getattr(file_types, upper_name))
        return resolved

    def _download_chain(
        self,
        *,
        package_api: dict[str, Any],
        request: ChainDownloadRequest,
    ) -> ChainDownloadResult:
        attempts: list[FileDownloadAttempt] = []
        downloaded_files: list[Path] = []
        warnings: list[str] = []
        errors: list[str] = []

        try:
            request.target_directory.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return self._build_chain_init_failure_result(
                chain_name=request.chain_name,
                file_types=request.file_types,
                target_directory=request.target_directory,
                exc=exc,
                normalized_reason=self._normalize_failure_reason(exc),
            )

        for file_type in request.file_types:
            before_files = self._list_files(request.target_directory)
            try:
                task = package_api["ScarpingTask"](
                    enabled_scrapers=[request.chain_name],
                    files_types=[file_type],
                    multiprocessing=1,
                    output_configuration={
                        "output_mode": "disk",
                        "base_storage_path": str(request.target_directory),
                    },
                )
                task.start(limit=request.limit, when_date=request.when_date, single_pass=True)
                task.join()
                after_files = self._list_files(request.target_directory)
                new_files = [path for path in after_files if path not in before_files]
                if not new_files:
                    failure_reason = "no files returned by upstream scraper"
                    attempts.append(
                        FileDownloadAttempt(
                            chain_name=request.chain_name,
                            file_type=file_type,
                            target_directory=request.target_directory,
                            expected_file_name=None,
                            discovered_file_name=None,
                            status=AttemptStatus.FAILED,
                            failure_reason=failure_reason,
                            failure_detail=FailureDetail(
                                chain_name=request.chain_name,
                                file_type=file_type,
                                exception_class_name="NoFilesReturned",
                                exception_message=failure_reason,
                                normalized_reason=failure_reason,
                            ),
                        )
                    )
                    errors.append(f"{request.chain_name} {file_type}: {failure_reason}")
                    continue

                downloaded_files.extend(new_files)
                attempts.append(
                    FileDownloadAttempt(
                        chain_name=request.chain_name,
                        file_type=file_type,
                        target_directory=request.target_directory,
                        expected_file_name=None,
                        discovered_file_name=new_files[0].name,
                        status=AttemptStatus.SUCCESS,
                        failure_reason=None,
                        downloaded_file_paths=list(new_files),
                    )
                )
            except Exception as exc:  # pragma: no cover - exercised via unit tests
                reason = self._normalize_failure_reason(exc)
                attempts.append(
                    FileDownloadAttempt(
                        chain_name=request.chain_name,
                        file_type=file_type,
                        target_directory=request.target_directory,
                        expected_file_name=None,
                        discovered_file_name=None,
                        status=AttemptStatus.FAILED,
                        failure_reason=reason,
                        failure_detail=FailureDetail(
                            chain_name=request.chain_name,
                            file_type=file_type,
                            exception_class_name=exc.__class__.__name__,
                            exception_message=str(exc),
                            normalized_reason=reason,
                        ),
                    )
                )
                errors.append(f"{request.chain_name} {file_type}: {reason}")

        if not downloaded_files:
            warnings.append(f"{request.chain_name}: no files downloaded")

        return ChainDownloadResult(
            chain_name=request.chain_name,
            success=all(attempt.status == AttemptStatus.SUCCESS for attempt in attempts if attempt.file_type in request.file_types) if attempts else False,
            requested_file_types=list(request.file_types),
            attempts=attempts,
            downloaded_files=sorted(downloaded_files),
            warnings=warnings,
            errors=errors,
        )

    def _build_chain_init_failure_result(
        self,
        *,
        chain_name: str,
        file_types: list[str],
        target_directory: Path,
        exc: Exception,
        normalized_reason: str,
    ) -> ChainDownloadResult:
        attempts = [
            FileDownloadAttempt(
                chain_name=chain_name,
                file_type="CHAIN_INIT",
                target_directory=target_directory,
                expected_file_name=None,
                discovered_file_name=None,
                status=AttemptStatus.FAILED,
                failure_reason=normalized_reason,
                failure_detail=FailureDetail(
                    chain_name=chain_name,
                    file_type="CHAIN_INIT",
                    exception_class_name=exc.__class__.__name__,
                    exception_message=str(exc),
                    normalized_reason=normalized_reason,
                ),
            )
        ]
        attempts.extend(
            FileDownloadAttempt(
                chain_name=chain_name,
                file_type=file_type,
                target_directory=target_directory,
                expected_file_name=None,
                discovered_file_name=None,
                status=AttemptStatus.SKIPPED,
                failure_reason=f"chain initialization failed: {normalized_reason}",
            )
            for file_type in file_types
        )
        return ChainDownloadResult(
            chain_name=chain_name,
            success=False,
            requested_file_types=list(file_types),
            attempts=attempts,
            downloaded_files=[],
            warnings=[f"{chain_name}: no files downloaded"],
            errors=[f"{chain_name} CHAIN_INIT: {normalized_reason}"],
        )

    @staticmethod
    def _normalize_failure_reason(exc: Exception) -> str:
        message = str(exc).strip()
        exception_class = exc.__class__.__name__
        if message:
            return f"{exception_class.lower()}: {message}"
        return exception_class.lower()

    @staticmethod
    def _default_chain_target(target_root: Path, chain_name: str) -> Path:
        slug = "shufersal" if chain_name == "SHUFERSAL" else "hazi_hinam"
        return target_root / slug

    @staticmethod
    def _list_files(target_directory: Path) -> list[Path]:
        if not target_directory.exists():
            return []
        return sorted(path for path in target_directory.rglob("*") if path.is_file())


class RetailerTransparencyDownloader:
    """Backward-compatible façade kept for existing call sites."""

    def __init__(self, manager: RetailChainsDownloadManager | None = None) -> None:
        self._manager = manager or RetailChainsDownloadManager()

    def download_files(
        self,
        target_root: str | Path = "data/raw/downloads",
        chains: list[str] | tuple[str, ...] | None = None,
        file_types: list[str] | tuple[str, ...] | None = None,
        when_date: date | datetime | None = None,
        limit: int | None = None,
        include_store_files: bool | None = None,
        prefer_full_price_files: bool | None = None,
    ) -> DownloadBatchResult:
        """Download chain files via the higher-level manager."""
        resolved_file_types = file_types
        if resolved_file_types is None and (
            include_store_files is not None or prefer_full_price_files is not None
        ):
            resolved_file_types = self._resolve_legacy_file_types(
                include_store_files=bool(include_store_files),
                prefer_full_price_files=bool(prefer_full_price_files),
            )
        return self._manager.download_chains(
            target_root=target_root,
            chains=chains,
            file_types=resolved_file_types,
            when_date=when_date,
            limit=limit,
        )

    def render_report(self, batch_result: DownloadBatchResult) -> str:
        """Render a readable report via the underlying manager."""
        return self._manager.render_report(batch_result)

    @staticmethod
    def _resolve_legacy_file_types(
        *,
        include_store_files: bool,
        prefer_full_price_files: bool,
    ) -> list[str]:
        selected: list[str] = []
        if include_store_files:
            selected.append("STORE_FILE")
        if prefer_full_price_files:
            selected.extend(["PRICE_FULL_FILE", "PRICE_FILE"])
        else:
            selected.append("PRICE_FILE")
        return selected


def download_all_supported_chains(
    target_root: str | Path = "data/raw/downloads",
    chains: list[str] | tuple[str, ...] | None = None,
    file_types: list[str] | tuple[str, ...] | None = None,
    when_date: date | datetime | None = None,
    limit: int | None = None,
) -> DownloadBatchResult:
    """Convenience API for one-call download execution."""
    return RetailChainsDownloadManager().download_chains(
        target_root=target_root,
        chains=chains,
        file_types=file_types,
        when_date=when_date,
        limit=limit,
    )
