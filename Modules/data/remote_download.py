"""Remote transparency-file download integration via il-supermarket-scraper."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from datetime import date, datetime
import importlib
from pathlib import Path
import shutil
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


class DownloadOutcome(str, Enum):
    """High-level outcome values for chain and batch reporting."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


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
    output_directory: Path
    attempts: list[FileDownloadAttempt] = field(default_factory=list)
    downloaded_files: list[Path] = field(default_factory=list)
    file_count: int = 0
    total_bytes: int = 0
    discovered_family_counts: dict[str, int] = field(default_factory=dict)
    unclassified_files: list[Path] = field(default_factory=list)
    naming_anomalies: list[str] = field(default_factory=list)
    status: str = "FAILED"
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
    outcome: str = DownloadOutcome.FAILED.value
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
        cleanup_before_download: bool = False,
        strict_success: bool = False,
    ) -> DownloadBatchResult:
        """Download requested file categories for requested supported chains."""
        self._validate_download_arguments(
            chains=chains,
            file_types=file_types,
            when_date=when_date,
            limit=limit,
            cleanup_before_download=cleanup_before_download,
        )
        started_at = datetime.utcnow()
        resolved_root = Path(target_root)

        try:
            package_api = self._load_package_api()
        except Exception as exc:
            finished_at = datetime.utcnow()
            normalized_reason = self._normalize_failure_reason(exc)
            source_requested = list(chains or SUPPORTED_CHAIN_ORDER)
            resolved_requested_chains = [self._normalize_chain_name(chain_name) for chain_name in source_requested]
            chain_results = [
                self._build_chain_init_failure_result(
                    chain_name=chain_name,
                    file_types=[self._normalize_file_type_name(ft) for ft in list(file_types or DEFAULT_FILE_TYPE_ORDER)],
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
                outcome=DownloadOutcome.FAILED.value,
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
            chain_result = self._download_chain(
                package_api=package_api,
                request=chain_request,
                cleanup_before_download=cleanup_before_download,
                strict_success=strict_success,
            )
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
        total_files_downloaded = sum(chain_result.file_count for chain_result in chain_results)
        overall_success = all(chain_result.success for chain_result in chain_results)
        chain_outcomes = [self._normalize_outcome(chain_result.outcome) for chain_result in chain_results]
        if chain_outcomes and all(outcome == DownloadOutcome.SUCCESS.value for outcome in chain_outcomes):
            batch_outcome = DownloadOutcome.SUCCESS.value
        elif any(outcome in (DownloadOutcome.SUCCESS.value, DownloadOutcome.PARTIAL.value) for outcome in chain_outcomes):
            batch_outcome = DownloadOutcome.PARTIAL.value
        else:
            batch_outcome = DownloadOutcome.FAILED.value

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
            success=overall_success,
            outcome=batch_outcome,
            warnings=batch_warnings,
            errors=batch_errors,
        )

    @staticmethod
    def _validate_download_arguments(
        *,
        chains: list[str] | tuple[str, ...] | None,
        file_types: list[str] | tuple[str, ...] | None,
        when_date: date | datetime | None,
        limit: int | None,
        cleanup_before_download: bool,
    ) -> None:
        if when_date is not None and not isinstance(when_date, (date, datetime)):
            raise ValueError("when_date must be a date, datetime, or None")
        if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0):
            raise ValueError("limit must be a positive integer or None")
        if not isinstance(cleanup_before_download, bool):
            raise ValueError("cleanup_before_download must be a bool")
        if chains is not None:
            requested_chains = [RetailChainsDownloadManager._normalize_chain_name(c) for c in chains]
            unsupported_chains = [c for c in requested_chains if c not in SUPPORTED_CHAIN_ORDER]
            if unsupported_chains:
                raise ValueError(
                    f"unsupported chains requested: {', '.join(sorted(set(unsupported_chains)))}"
                )
        if file_types is not None:
            requested_file_types = [RetailChainsDownloadManager._normalize_file_type_name(ft) for ft in file_types]
            unsupported_file_types = [ft for ft in requested_file_types if ft not in DEFAULT_FILE_TYPE_ORDER]
            if unsupported_file_types:
                raise ValueError(
                    f"unsupported file_types requested: {', '.join(sorted(set(unsupported_file_types)))}"
                )

    def render_report(self, batch_result: DownloadBatchResult) -> str:
        """Render a deterministic human-readable report for batch results."""
        try:
            lines = [
                "Download batch summary",
                f"root={self._safe_str(batch_result.root_target_directory)}",
                f"chains={','.join(self._normalize_chain_name(c) for c in batch_result.requested_chains)}",
                f"attempts_success={batch_result.total_successful_attempts}",
                f"attempts_failed={batch_result.total_failed_attempts}",
                f"attempts_skipped={batch_result.total_skipped_attempts}",
                f"files_downloaded={batch_result.total_files_downloaded}",
                f"overall_success={batch_result.success}",
                f"overall_outcome={self._normalize_outcome(getattr(batch_result, 'outcome', None))}",
            ]

            for chain_result in batch_result.chain_results:
                lines.append("")
                lines.append(f"Chain: {self._normalize_chain_name(chain_result.chain_name)}")
                lines.append(f"- output_directory={self._safe_str(chain_result.output_directory)}")
                lines.append(f"- file_count={chain_result.file_count}")
                lines.append(f"- total_bytes={chain_result.total_bytes}")
                families_text = ", ".join(
                    f"{family}={count}" for family, count in sorted(chain_result.discovered_family_counts.items())
                ) or "none"
                lines.append(f"- discovered_families={families_text}")
                lines.append(f"- unclassified_files={len(chain_result.unclassified_files)}")
                lines.append(f"- naming_anomalies={len(chain_result.naming_anomalies)}")
                lines.append(f"- status={chain_result.status}")
                sample_paths = ", ".join(self._safe_str(path) for path in chain_result.downloaded_files[:5]) or "none"
                lines.append(f"- sample_files={sample_paths}")
                if chain_result.naming_anomalies:
                    sample_anomaly = "; ".join(chain_result.naming_anomalies[:3])
                    lines.append(f"- anomaly_samples={self._safe_str(sample_anomaly)}")
                for attempt in chain_result.attempts:
                    status_text = self._normalize_attempt_status(attempt.status)
                    line = f"- {self._normalize_file_type_name(attempt.file_type)}: {status_text}"
                    if status_text == AttemptStatus.SUCCESS.value:
                        path_text = ", ".join(self._safe_str(path) for path in attempt.downloaded_file_paths) or "none"
                        line += f" | paths={path_text}"
                    else:
                        reason = attempt.failure_reason or "unknown failure"
                        line += f" | reason={self._safe_str(reason)}"
                    if attempt.warnings:
                        line += f" | warnings={'; '.join(self._safe_str(w) for w in attempt.warnings)}"
                    lines.append(line)
                for warning in chain_result.warnings:
                    lines.append(f"- WARNING: {self._safe_str(warning)}")
                for error in chain_result.errors:
                    lines.append(f"- ERROR: {self._safe_str(error)}")
            return "\n".join(lines)
        except Exception as exc:  # pragma: no cover - defensive fallback
            return (
                "Download batch summary\n"
                f"overall_success={self._safe_str(getattr(batch_result, 'success', False))}\n"
                f"report_render_error={exc.__class__.__name__}: {self._safe_str(exc)}"
            )

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
        _ = package_api["ScraperFactory"]
        supported = {"SHUFERSAL", "HAZI_HINAM"}
        chain_names = list(requested_chains) if requested_chains is not None else list(SUPPORTED_CHAIN_ORDER)
        resolved: list[str] = []
        for chain_name in chain_names:
            canonical = RetailChainsDownloadManager._normalize_chain_name(chain_name)
            if canonical in supported:
                resolved.append(canonical)
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
            upper_name = RetailChainsDownloadManager._normalize_file_type_name(file_type_name)
            if hasattr(file_types, upper_name):
                resolved.append(upper_name)
        return resolved

    def _download_chain(
        self,
        *,
        package_api: dict[str, Any],
        request: ChainDownloadRequest,
        cleanup_before_download: bool,
        strict_success: bool,
    ) -> ChainDownloadResult:
        attempts: list[FileDownloadAttempt] = []
        downloaded_files: list[Path] = []
        warnings: list[str] = []
        errors: list[str] = []

        try:
            request.target_directory.mkdir(parents=True, exist_ok=True)
            if cleanup_before_download:
                self._cleanup_target_directory(request.target_directory)
        except Exception as exc:
            return self._build_chain_init_failure_result(
                chain_name=request.chain_name,
                file_types=request.file_types,
                target_directory=request.target_directory,
                exc=exc,
                normalized_reason=self._normalize_failure_reason(exc),
            )

        for file_type in request.file_types:
            normalized_chain = self._normalize_chain_name(request.chain_name)
            normalized_file_type = self._normalize_file_type_name(file_type)
            before_files = self._list_files(request.target_directory)
            try:
                upstream_scraper = self._resolve_upstream_scraper_identifier(
                    package_api=package_api,
                    chain_name=request.chain_name,
                )
                upstream_file_type = self._resolve_upstream_file_type_identifier(
                    package_api=package_api,
                    file_type=file_type,
                )
                task = package_api["ScarpingTask"](
                    enabled_scrapers=[upstream_scraper],
                    files_types=[upstream_file_type],
                    multiprocessing=1,
                    output_configuration={
                        "output_mode": "disk",
                        "base_storage_path": str(request.target_directory),
                    },
                )
                task.start(limit=request.limit, when_date=request.when_date, single_pass=True)
                task.join()
                task_failure = self._extract_task_failure(task)
                if task_failure is not None:
                    failure_attempt = self._build_failed_attempt(
                        chain_name=request.chain_name,
                        file_type=file_type,
                        target_directory=request.target_directory,
                        exc=task_failure,
                    )
                    attempts.append(failure_attempt)
                    errors.append(
                        f"{failure_attempt.chain_name} {failure_attempt.file_type}: {failure_attempt.failure_reason}"
                    )
                    continue
                after_files = self._list_files(request.target_directory)
                new_files = [path for path in after_files if path not in before_files]
                if not new_files:
                    failure_reason = "no files returned by upstream scraper"
                    attempts.append(
                        FileDownloadAttempt(
                            chain_name=normalized_chain,
                            file_type=normalized_file_type,
                            target_directory=request.target_directory,
                            expected_file_name=None,
                            discovered_file_name=None,
                            status=AttemptStatus.FAILED,
                            failure_reason=failure_reason,
                            failure_detail=FailureDetail(
                                chain_name=normalized_chain,
                                file_type=normalized_file_type,
                                exception_class_name="NoFilesReturned",
                                exception_message=failure_reason,
                                normalized_reason=failure_reason,
                            ),
                        )
                    )
                    errors.append(f"{normalized_chain} {normalized_file_type}: {failure_reason}")
                    continue

                downloaded_files.extend(new_files)
                attempts.append(
                    FileDownloadAttempt(
                        chain_name=normalized_chain,
                        file_type=normalized_file_type,
                        target_directory=request.target_directory,
                        expected_file_name=None,
                        discovered_file_name=new_files[0].name,
                        status=AttemptStatus.SUCCESS,
                        failure_reason=None,
                        downloaded_file_paths=list(new_files),
                    )
                )
            except Exception as exc:  # pragma: no cover - exercised via unit tests
                failure_attempt = self._build_failed_attempt(
                    chain_name=request.chain_name,
                    file_type=file_type,
                    target_directory=request.target_directory,
                    exc=exc,
                )
                attempts.append(failure_attempt)
                errors.append(
                    f"{failure_attempt.chain_name} {failure_attempt.file_type}: {failure_attempt.failure_reason}"
                )

        inventory = self._discover_downloaded_files(request.target_directory)
        downloaded_files = list(inventory["all_files"])
        total_bytes = sum(path.stat().st_size for path in downloaded_files if path.exists())
        if inventory["naming_anomalies"]:
            warnings.append(
                (
                    f"{self._normalize_chain_name(request.chain_name)}: detected upstream naming anomalies "
                    "(wrapper kept original names)"
                )
            )
        if not downloaded_files:
            warnings.append(f"{self._normalize_chain_name(request.chain_name)}: no files downloaded")
        failed_attempts = [attempt for attempt in attempts if attempt.status == AttemptStatus.FAILED]
        chain_outcome = DownloadOutcome.FAILED
        if strict_success:
            success = bool(attempts) and not failed_attempts and bool(downloaded_files)
            if success:
                chain_outcome = DownloadOutcome.SUCCESS
            elif downloaded_files:
                chain_outcome = DownloadOutcome.PARTIAL
        else:
            success = bool(downloaded_files)
            if success and failed_attempts:
                warnings.append(
                    f"{self._normalize_chain_name(request.chain_name)}: files exist on disk despite failed attempts"
                )
            if success and failed_attempts:
                chain_outcome = DownloadOutcome.PARTIAL
            elif success:
                chain_outcome = DownloadOutcome.SUCCESS
        return ChainDownloadResult(
            chain_name=self._normalize_chain_name(request.chain_name),
            success=success,
            requested_file_types=[self._normalize_file_type_name(f) for f in request.file_types],
            output_directory=request.target_directory,
            attempts=attempts,
            downloaded_files=downloaded_files,
            file_count=len(downloaded_files),
            total_bytes=total_bytes,
            discovered_family_counts=dict(inventory["family_counts"]),
            unclassified_files=list(inventory["unclassified_files"]),
            naming_anomalies=list(inventory["naming_anomalies"]),
            status=status,
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
        normalized_chain = self._normalize_chain_name(chain_name)
        normalized_file_types = [self._normalize_file_type_name(file_type) for file_type in file_types]
        attempts = [
            FileDownloadAttempt(
                chain_name=normalized_chain,
                file_type="CHAIN_INIT",
                target_directory=target_directory,
                expected_file_name=None,
                discovered_file_name=None,
                status=AttemptStatus.FAILED,
                failure_reason=normalized_reason,
                failure_detail=FailureDetail(
                    chain_name=normalized_chain,
                    file_type="CHAIN_INIT",
                    exception_class_name=exc.__class__.__name__,
                    exception_message=self._safe_str(exc),
                    normalized_reason=normalized_reason,
                ),
            )
        ]
        attempts.extend(
            FileDownloadAttempt(
                chain_name=normalized_chain,
                file_type=file_type,
                target_directory=target_directory,
                expected_file_name=None,
                discovered_file_name=None,
                status=AttemptStatus.SKIPPED,
                failure_reason=f"chain initialization failed: {normalized_reason}",
            )
            for file_type in normalized_file_types
        )
        return ChainDownloadResult(
            chain_name=normalized_chain,
            success=False,
            requested_file_types=normalized_file_types,
            output_directory=target_directory,
            attempts=attempts,
            downloaded_files=[],
            file_count=0,
            total_bytes=0,
            discovered_family_counts={},
            unclassified_files=[],
            naming_anomalies=[],
            status="FAILED",
            warnings=[f"{normalized_chain}: no files downloaded"],
            errors=[f"{normalized_chain} CHAIN_INIT: {normalized_reason}"],
        )

    @staticmethod
    def _normalize_failure_reason(exc: Exception) -> str:
        message = str(exc).strip()
        exception_class = exc.__class__.__name__
        lowered_message = message.lower()
        lowered_class = exception_class.lower()
        if (
            "scraperfactory" in lowered_message
            or "invalid scraper" in lowered_message
            or "enabled_scrapers" in lowered_message
            or (lowered_class == "keyerror" and "scraper" in lowered_message)
        ):
            return "invalid scraper identifier passed to upstream package"
        if message:
            return f"{exception_class.lower()}: {message}"
        return exception_class.lower()

    @staticmethod
    def _safe_str(value: Any) -> str:
        if value is None:
            return ""
        try:
            return str(value)
        except Exception:
            return repr(value)

    @staticmethod
    def _normalize_chain_name(value: Any) -> str:
        token = RetailChainsDownloadManager._extract_enum_like_token(value)
        return token.upper()

    @staticmethod
    def _normalize_file_type_name(value: Any) -> str:
        token = RetailChainsDownloadManager._extract_enum_like_token(value)
        return token.upper()

    @staticmethod
    def _normalize_attempt_status(status: Any) -> str:
        if isinstance(status, AttemptStatus):
            return status.value
        if hasattr(status, "value"):
            return RetailChainsDownloadManager._safe_str(getattr(status, "value")).upper()
        return RetailChainsDownloadManager._safe_str(status).upper() or AttemptStatus.FAILED.value

    @staticmethod
    def _normalize_outcome(outcome: Any) -> str:
        if isinstance(outcome, DownloadOutcome):
            return outcome.value
        if hasattr(outcome, "value"):
            return RetailChainsDownloadManager._safe_str(getattr(outcome, "value")).upper()
        normalized = RetailChainsDownloadManager._safe_str(outcome).strip().upper()
        if normalized in (DownloadOutcome.SUCCESS.value, DownloadOutcome.PARTIAL.value, DownloadOutcome.FAILED.value):
            return normalized
        if normalized == "SUCCESS_WITH_WARNINGS":
            return DownloadOutcome.PARTIAL.value
        return DownloadOutcome.FAILED.value

    @staticmethod
    def _extract_enum_like_token(value: Any) -> str:
        if hasattr(value, "name"):
            name_value = getattr(value, "name")
            if isinstance(name_value, str) and name_value.strip():
                return name_value.strip()
        raw = RetailChainsDownloadManager._safe_str(value).strip()
        raw = raw.strip("<>").strip()
        if "." in raw:
            raw = raw.split(".")[-1]
        return raw

    @staticmethod
    def _resolve_upstream_scraper_identifier(*, package_api: dict[str, Any], chain_name: str) -> Any:
        scraper_factory = package_api["ScraperFactory"]
        normalized_chain = RetailChainsDownloadManager._normalize_chain_name(chain_name)
        enum_members = getattr(scraper_factory, "__members__", None)
        if isinstance(enum_members, dict) and normalized_chain in enum_members:
            member = enum_members[normalized_chain]
            if isinstance(getattr(member, "value", None), str):
                return normalized_chain
            return member
        return normalized_chain

    @staticmethod
    def _resolve_upstream_file_type_identifier(*, package_api: dict[str, Any], file_type: str) -> Any:
        file_type_filters = package_api["FileTypesFilters"]
        normalized_file_type = RetailChainsDownloadManager._normalize_file_type_name(file_type)
        enum_members = getattr(file_type_filters, "__members__", None)
        if isinstance(enum_members, dict) and normalized_file_type in enum_members:
            member = enum_members[normalized_file_type]
            if isinstance(getattr(member, "value", None), str):
                return normalized_file_type
            return member
        return normalized_file_type

    @staticmethod
    def _extract_task_failure(task: Any) -> Exception | None:
        for attribute in ("exception", "error"):
            value = getattr(task, attribute, None)
            if isinstance(value, Exception):
                return value
        for attribute in ("exceptions", "errors", "thread_exceptions"):
            value = getattr(task, attribute, None)
            if isinstance(value, list) and value:
                first_item = value[0]
                if isinstance(first_item, Exception):
                    return first_item
                return RuntimeError(RetailChainsDownloadManager._safe_str(first_item))
        return None

    def _build_failed_attempt(
        self,
        *,
        chain_name: str,
        file_type: str,
        target_directory: Path,
        exc: Exception,
    ) -> FileDownloadAttempt:
        normalized_chain = self._normalize_chain_name(chain_name)
        normalized_file_type = self._normalize_file_type_name(file_type)
        reason = self._normalize_failure_reason(exc)
        return FileDownloadAttempt(
            chain_name=normalized_chain,
            file_type=normalized_file_type,
            target_directory=target_directory,
            expected_file_name=None,
            discovered_file_name=None,
            status=AttemptStatus.FAILED,
            failure_reason=reason,
            failure_detail=FailureDetail(
                chain_name=normalized_chain,
                file_type=normalized_file_type,
                exception_class_name=exc.__class__.__name__,
                exception_message=self._safe_str(exc),
                normalized_reason=reason,
            ),
        )

    @staticmethod
    def _default_chain_target(target_root: Path, chain_name: str) -> Path:
        normalized = RetailChainsDownloadManager._normalize_chain_name(chain_name)
        if normalized == "SHUFERSAL":
            slug = "shufersal"
        elif normalized == "HAZI_HINAM":
            slug = "hazi_hinam"
        else:
            slug = normalized.lower() or "unknown_chain"
        return target_root / slug

    @staticmethod
    def _list_files(target_directory: Path) -> list[Path]:
        if not target_directory.exists():
            return []
        return sorted(path for path in target_directory.rglob("*") if path.is_file())

    @classmethod
    def _discover_downloaded_files(cls, target_directory: Path) -> dict[str, Any]:
        all_files = cls._list_files(target_directory)
        family_counts: dict[str, int] = {}
        unclassified_files: list[Path] = []
        naming_anomalies: list[str] = []
        for path in all_files:
            family = cls._classify_file_family(path.name)
            if family is None:
                unclassified_files.append(path)
            else:
                family_counts[family] = family_counts.get(family, 0) + 1
            anomaly = cls._detect_naming_anomaly(path.name)
            if anomaly is not None:
                naming_anomalies.append(f"{path.name}: {anomaly}")
        return {
            "all_files": all_files,
            "family_counts": family_counts,
            "unclassified_files": unclassified_files,
            "naming_anomalies": naming_anomalies,
        }

    @staticmethod
    def _classify_file_family(file_name: str) -> str | None:
        normalized = file_name.upper()
        if "PRICEFULL" in normalized or "PRICE_FULL" in normalized:
            return "PriceFull"
        if "PROMOFULL" in normalized or "PROMO_FULL" in normalized:
            return "PromoFull"
        if "STORE" in normalized or "STORES" in normalized:
            return "Stores"
        if "PRICE" in normalized:
            return "Price"
        if "PROMO" in normalized:
            return "Promo"
        return None

    @staticmethod
    def _detect_naming_anomaly(file_name: str) -> str | None:
        normalized = file_name.lower()
        if normalized.endswith(".gz.xml.xml"):
            return "double xml suffix after gz marker"
        return None

    @staticmethod
    def _cleanup_target_directory(target_directory: Path) -> None:
        resolved = target_directory.resolve()
        if resolved == Path(resolved.anchor):
            raise ValueError("refusing to clean filesystem root")
        if not target_directory.exists():
            return
        for child in target_directory.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
            else:
                shutil.rmtree(child)


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
        cleanup_before_download: bool = False,
        strict_success: bool = False,
        include_store_files: bool | None = None,
        prefer_full_price_files: bool | None = None,
    ) -> DownloadBatchResult:
        """Download chain files via the higher-level manager."""
        if file_types is not None and (
            include_store_files is not None or prefer_full_price_files is not None
        ):
            raise ValueError(
                "file_types cannot be combined with include_store_files/prefer_full_price_files"
            )
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
            cleanup_before_download=cleanup_before_download,
            strict_success=strict_success,
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
    cleanup_before_download: bool = False,
    strict_success: bool = False,
) -> DownloadBatchResult:
    """Convenience API for one-call download execution."""
    return RetailChainsDownloadManager().download_chains(
        target_root=target_root,
        chains=chains,
        file_types=file_types,
        when_date=when_date,
        limit=limit,
        cleanup_before_download=cleanup_before_download,
        strict_success=strict_success,
    )
