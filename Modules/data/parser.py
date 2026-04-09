"""Core parser infrastructure for MVP local file ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class FileFormat(str, Enum):
    """Supported source file formats for MVP parsing."""

    CSV = "csv"
    JSON = "json"


class UnsupportedFileFormatError(ValueError):
    """Raised when parsing is requested for an unsupported file format."""


@dataclass(slots=True)
class ParsedProductRecord:
    """Internal representation of a parsed product row."""

    source_row_number: int
    barcode: str
    product_name: str
    normalized_name: str
    brand: str | None = None
    unit_name: str | None = None


@dataclass(slots=True)
class ParsedPriceRecord:
    """Internal representation of a parsed price row."""

    source_row_number: int
    chain_code: str
    store_code: str
    barcode: str
    price_text: str
    currency: str
    price_date_text: str


@dataclass(slots=True)
class ParsingError:
    """Structured parsing error for malformed input rows."""

    row_number: int
    field_name: str
    message: str
    raw_value: str | None = None


@dataclass(slots=True)
class ParsingErrorCollection:
    """Collects structured parsing errors in deterministic insertion order."""

    errors: list[ParsingError] = field(default_factory=list)

    def add(self, error: ParsingError) -> None:
        """Store one structured parsing error."""
        self.errors.append(error)

    @property
    def count(self) -> int:
        """Return number of collected parsing errors."""
        return len(self.errors)

    def is_empty(self) -> bool:
        """Return True when no parsing errors were recorded."""
        return self.count == 0


@dataclass(slots=True)
class ParsingSummary:
    """Minimal aggregate parsing outcomes for one file."""

    file_path: Path
    file_format: FileFormat
    accepted_rows: int = 0
    rejected_rows: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def total_rows(self) -> int:
        """Return total processed rows."""
        return self.accepted_rows + self.rejected_rows


class FileParser:
    """Narrow helper APIs for file-format handling in concrete parsers."""

    _SUFFIX_TO_FORMAT: dict[str, FileFormat] = {
        ".csv": FileFormat.CSV,
        ".json": FileFormat.JSON,
    }

    @classmethod
    def detect_format(cls, file_path: str | Path) -> FileFormat:
        """Detect supported file format from a file suffix."""
        suffix = Path(file_path).suffix.lower()
        detected = cls._SUFFIX_TO_FORMAT.get(suffix)
        if detected is None:
            raise UnsupportedFileFormatError(f"unsupported file format: {suffix or '<none>'}")
        return detected

    @staticmethod
    def create_summary(file_path: str | Path) -> ParsingSummary:
        """Create default parsing summary for a source file."""
        resolved_path = Path(file_path)
        return ParsingSummary(
            file_path=resolved_path,
            file_format=FileParser.detect_format(resolved_path),
        )

    @staticmethod
    def create_error_collection() -> ParsingErrorCollection:
        """Create an empty structured parsing error collection."""
        return ParsingErrorCollection()
