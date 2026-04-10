"""Discovery and orchestration for importing downloaded retailer files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from Modules.data.data_loader import LoadMode, LoadResult, PriceDataLoader

ImportEntity = Literal["stores", "products", "prices"]


@dataclass(slots=True)
class DiscoveredRetailerFile:
    """One discovered local file mapped to an import entity."""

    entity: ImportEntity
    path: Path


@dataclass(slots=True)
class BatchFileImportResult:
    """One per-file load outcome included in a batch summary."""

    discovered_file: DiscoveredRetailerFile
    load_result: LoadResult


@dataclass(slots=True)
class BatchImportSummary:
    """Unified batch import summary across discovery and parse/load phases."""

    root_directory: Path
    discovered_count: int = 0
    imported_count: int = 0
    skipped_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    accepted_rows: int = 0
    rejected_rows: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    file_results: list[BatchFileImportResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Return True when no per-file failures were recorded."""
        return self.failed_count == 0 and not self.errors


class DownloadedRetailerFileDiscovery:
    """Discovers parseable retailer files in a downloaded directory tree."""

    _SUPPORTED_SUFFIXES = {".csv", ".json"}

    def discover(self, root_directory: str | Path) -> tuple[list[DiscoveredRetailerFile], list[str]]:
        """Return discovered entity-mapped files and discovery warnings."""
        root = Path(root_directory)
        if not root.exists():
            return [], [f"download root does not exist: {root}"]

        discovered: list[DiscoveredRetailerFile] = []
        warnings: list[str] = []

        for file_path in sorted(path for path in root.rglob("*") if path.is_file()):
            if file_path.suffix.lower() not in self._SUPPORTED_SUFFIXES:
                warnings.append(f"skipped unsupported file extension: {file_path}")
                continue

            entity = self._classify_entity(file_path)
            if entity is None:
                warnings.append(f"skipped unrecognized retailer file: {file_path}")
                continue
            discovered.append(DiscoveredRetailerFile(entity=entity, path=file_path))

        return discovered, warnings

    @staticmethod
    def _classify_entity(file_path: Path) -> ImportEntity | None:
        token = file_path.name.lower()
        if "store" in token:
            return "stores"
        if "product" in token:
            return "products"
        if "price" in token:
            return "prices"
        return None


class DownloadedImportOrchestrator:
    """Connects downloaded-file discovery into parser and loader entry points."""

    _ENTITY_PRIORITY: dict[ImportEntity, int] = {
        "stores": 0,
        "products": 1,
        "prices": 2,
    }

    def __init__(
        self,
        loader: PriceDataLoader,
        discovery: DownloadedRetailerFileDiscovery | None = None,
    ) -> None:
        self._loader = loader
        self._discovery = discovery or DownloadedRetailerFileDiscovery()

    def import_downloaded_tree(
        self,
        root_directory: str | Path,
        mode: LoadMode = "append",
    ) -> BatchImportSummary:
        """Run one deterministic flow from downloaded files to DB loading."""
        root = Path(root_directory)
        discovered_files, discovery_warnings = self._discovery.discover(root)

        summary = BatchImportSummary(
            root_directory=root,
            discovered_count=len(discovered_files),
            warnings=list(discovery_warnings),
        )

        ordered_files = sorted(
            discovered_files,
            key=lambda item: (self._ENTITY_PRIORITY[item.entity], str(item.path)),
        )

        for discovered_file in ordered_files:
            load_result = self._load_discovered_file(discovered_file=discovered_file, mode=mode)
            summary.file_results.append(
                BatchFileImportResult(discovered_file=discovered_file, load_result=load_result)
            )
            summary.imported_count += 1
            summary.accepted_rows += load_result.accepted_count
            summary.rejected_rows += load_result.rejected_count
            summary.warnings.extend(load_result.warnings)

            if load_result.success:
                summary.success_count += 1
            else:
                summary.failed_count += 1
                summary.errors.extend(load_result.errors)

        summary.skipped_count = max(summary.discovered_count - summary.imported_count, 0)
        return summary

    def _load_discovered_file(self, discovered_file: DiscoveredRetailerFile, mode: LoadMode) -> LoadResult:
        if discovered_file.entity == "stores":
            return self._loader.load_stores(discovered_file.path, mode=mode)
        if discovered_file.entity == "products":
            return self._loader.load_products(discovered_file.path, mode=mode)
        return self._loader.load_prices(discovered_file.path, mode=mode)
