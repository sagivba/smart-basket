"""Core parser infrastructure for MVP local file ingestion."""

from __future__ import annotations

import csv
import gzip
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, TypeVar
import xml.etree.ElementTree as ET

from Modules.utils.text_utils import normalize_product_name, normalize_whitespace
from Modules.utils.validators import validate_barcode, validate_required_text


class FileFormat(str, Enum):
    """Supported source file formats for MVP parsing."""

    CSV = "csv"
    JSON = "json"
    XML = "xml"


class UnsupportedFileFormatError(ValueError):
    """Raised when parsing is requested for an unsupported file format."""


class MalformedFileContentError(ValueError):
    """Raised when file content cannot be parsed as valid structured rows."""


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
class ParsedStoreRecord:
    """Internal representation of a parsed chain/store row."""

    source_row_number: int
    chain_code: str
    chain_name: str
    store_code: str
    store_name: str
    city: str | None = None
    address: str | None = None
    is_active: str | None = None


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

    def extend(self, errors: list[ParsingError]) -> None:
        """Store multiple parsing errors while preserving insertion order."""
        self.errors.extend(errors)

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

    def record_accepted(self) -> None:
        """Increment accepted row count by one."""
        self.accepted_rows += 1

    def record_rejected(self) -> None:
        """Increment rejected row count by one."""
        self.rejected_rows += 1

    def add_warning(self, message: str) -> None:
        """Store one summary warning message."""
        self.warnings.append(message)


@dataclass(slots=True)
class ParsingBatchSummary:
    """Aggregate parsing outcomes for a deterministic file batch run."""

    batch_name: str
    file_count: int = 0
    accepted_rows: int = 0
    rejected_rows: int = 0
    warnings: list[str] = field(default_factory=list)
    file_summaries: list[ParsingSummary] = field(default_factory=list)

    def add_file_summary(self, summary: ParsingSummary) -> None:
        """Merge one per-file summary into this batch summary."""
        self.file_count += 1
        self.accepted_rows += summary.accepted_rows
        self.rejected_rows += summary.rejected_rows
        self.file_summaries.append(summary)
        self.warnings.extend(summary.warnings)


class FileParser:
    """Narrow helper APIs for file-format handling in concrete parsers."""

    _SUFFIX_TO_FORMAT: dict[str, FileFormat] = {
        ".csv": FileFormat.CSV,
        ".json": FileFormat.JSON,
        ".xml": FileFormat.XML,
    }

    @classmethod
    def detect_format(cls, file_path: str | Path) -> FileFormat:
        """Detect supported file format from a file suffix."""
        suffix = _detect_effective_suffix(file_path)
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


@dataclass(slots=True)
class _RowValidationError(ValueError):
    """Internal row-level validation error with structured metadata."""

    field_name: str
    message: str
    raw_value: str | None = None


def _normalize_row(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Normalize row keys for deterministic field lookup."""
    return {normalize_whitespace(str(key)).lower(): value for key, value in raw_row.items()}


def _strip_xml_namespace(tag: str) -> str:
    """Normalize XML tag names by removing optional namespaces."""
    if "}" in tag:
        tag = tag.split("}", maxsplit=1)[1]
    return tag


def _detect_effective_suffix(file_path: str | Path) -> str:
    """Detect actual payload suffix, including .gz-wrapped payloads."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix != ".gz":
        return suffix
    return Path(path.stem).suffix.lower()


def _open_text_file(file_path: str | Path):
    """Open supported text payloads, including optional gzip compression."""
    path = Path(file_path)
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("r", encoding="utf-8", newline="")


def _xml_row_to_dict(element: ET.Element) -> dict[str, str]:
    """Convert one XML row element into a flat dict of direct children text."""
    row: dict[str, str] = {}
    for child in list(element):
        key = normalize_whitespace(_strip_xml_namespace(child.tag)).lower()
        value = normalize_whitespace(child.text or "")
        row[key] = value
    return row


def _read_xml_rows(
    file_path: str | Path,
    *,
    required_aliases: set[str],
) -> list[tuple[int, dict[str, str]]]:
    """Read XML rows that contain known aliases for target parser fields."""
    try:
        with _open_text_file(file_path) as xml_file:
            root = ET.parse(xml_file).getroot()
    except ET.ParseError as exc:
        raise MalformedFileContentError("malformed XML content") from exc

    rows: list[tuple[int, dict[str, str]]] = []
    row_number = 1
    for element in root.iter():
        children = list(element)
        if not children:
            continue
        row = _xml_row_to_dict(element)
        if required_aliases.intersection(row.keys()):
            rows.append((row_number, row))
            row_number += 1

    return rows


def _read_rows(file_path: str | Path) -> tuple[FileFormat, list[tuple[int, dict[str, Any]]]]:
    """Read a supported file into a deterministic sequence of row dictionaries."""
    format_type = FileParser.detect_format(file_path)
    path = Path(file_path)

    if format_type == FileFormat.CSV:
        try:
            with _open_text_file(path) as csv_file:
                reader = csv.DictReader(csv_file)
                if reader.fieldnames is None:
                    raise MalformedFileContentError("CSV file must include a header row")
                return format_type, [
                    (index, dict(row))
                    for index, row in enumerate(reader, start=2)
                ]
        except csv.Error as exc:
            raise MalformedFileContentError("malformed CSV content") from exc

    if format_type == FileFormat.JSON:
        try:
            with _open_text_file(path) as json_file:
                payload = json.load(json_file)
        except json.JSONDecodeError as exc:
            raise MalformedFileContentError("malformed JSON content") from exc

        if not isinstance(payload, list):
            raise MalformedFileContentError("JSON content must be a list of row objects")

        rows: list[tuple[int, dict[str, Any]]] = []
        for index, row in enumerate(payload, start=1):
            if not isinstance(row, dict):
                raise MalformedFileContentError("JSON rows must be objects")
            rows.append((index, row))
        return format_type, rows

    return format_type, _read_xml_rows(
        path,
        required_aliases={
            "chainid",
            "chain_code",
            "storeid",
            "store_code",
            "itemcode",
            "barcode",
            "price",
            "itemprice",
            "product_name",
            "itemname",
        },
    )


def _get_required_field(
    row: dict[str, Any],
    aliases: tuple[str, ...],
    *,
    target_field: str,
    row_number: int,
) -> str:
    """Get a normalized required field value from one input row."""
    for alias in aliases:
        if alias in row:
            raw_value = row.get(alias)
            if raw_value is None:
                break
            try:
                validated = validate_required_text(str(raw_value), target_field)
                return normalize_whitespace(validated)
            except (TypeError, ValueError) as exc:
                raise _RowValidationError(target_field, str(exc), str(raw_value)) from exc

    raise _RowValidationError(target_field, f"{target_field} is required")


def _get_optional_field(row: dict[str, Any], aliases: tuple[str, ...]) -> str | None:
    """Get an optional field and normalize empty values to None."""
    for alias in aliases:
        if alias in row:
            raw_value = row.get(alias)
            if raw_value is None:
                return None
            normalized = normalize_whitespace(str(raw_value))
            return normalized or None
    return None


def _build_product_record(row_number: int, raw_row: dict[str, Any]) -> ParsedProductRecord:
    """Build one validated ParsedProductRecord from an input row."""
    row = _normalize_row(raw_row)

    barcode_text = _get_required_field(
        row,
        ("barcode", "product_barcode"),
        target_field="barcode",
        row_number=row_number,
    )
    try:
        barcode = validate_barcode(barcode_text)
    except (TypeError, ValueError) as exc:
        raise _RowValidationError("barcode", str(exc), barcode_text) from exc

    product_name = _get_required_field(
        row,
        ("product_name", "name", "product"),
        target_field="product_name",
        row_number=row_number,
    )
    normalized_name = normalize_product_name(product_name)

    return ParsedProductRecord(
        source_row_number=row_number,
        barcode=barcode,
        product_name=product_name,
        normalized_name=normalized_name,
        brand=_get_optional_field(row, ("brand",)),
        unit_name=_get_optional_field(row, ("unit_name", "unit")),
    )


def _build_price_record(row_number: int, raw_row: dict[str, Any]) -> ParsedPriceRecord:
    """Build one validated ParsedPriceRecord from an input row."""
    row = _normalize_row(raw_row)

    chain_code = _get_required_field(
        row,
        ("chain_code", "chain", "chainid"),
        target_field="chain_code",
        row_number=row_number,
    )
    store_code = _get_required_field(
        row,
        ("store_code", "store", "storeid"),
        target_field="store_code",
        row_number=row_number,
    )
    barcode_text = _get_required_field(
        row,
        ("barcode", "product_barcode", "itemcode"),
        target_field="barcode",
        row_number=row_number,
    )
    try:
        barcode = validate_barcode(barcode_text)
    except (TypeError, ValueError) as exc:
        raise _RowValidationError("barcode", str(exc), barcode_text) from exc

    price_text = _get_required_field(
        row,
        ("price", "price_text", "itemprice"),
        target_field="price",
        row_number=row_number,
    )
    currency = _get_required_field(
        row,
        ("currency",),
        target_field="currency",
        row_number=row_number,
    )
    price_date_text = _get_required_field(
        row,
        ("price_date", "price_date_text", "date", "pricedate", "updatedate"),
        target_field="price_date",
        row_number=row_number,
    )

    return ParsedPriceRecord(
        source_row_number=row_number,
        chain_code=chain_code,
        store_code=store_code,
        barcode=barcode,
        price_text=price_text,
        currency=currency,
        price_date_text=price_date_text,
    )


def _build_store_record(row_number: int, raw_row: dict[str, Any]) -> ParsedStoreRecord:
    """Build one validated ParsedStoreRecord from an input row."""
    row = _normalize_row(raw_row)

    chain_code = _get_required_field(
        row,
        ("chain_code", "chain", "chainid"),
        target_field="chain_code",
        row_number=row_number,
    )
    chain_name = _get_required_field(
        row,
        ("chain_name", "chain", "chainname"),
        target_field="chain_name",
        row_number=row_number,
    )
    store_code = _get_required_field(
        row,
        ("store_code", "store", "storeid"),
        target_field="store_code",
        row_number=row_number,
    )
    store_name = _get_required_field(
        row,
        ("store_name", "name", "store", "storename"),
        target_field="store_name",
        row_number=row_number,
    )

    return ParsedStoreRecord(
        source_row_number=row_number,
        chain_code=chain_code,
        chain_name=chain_name,
        store_code=store_code,
        store_name=store_name,
        city=_get_optional_field(row, ("city", "cityname")),
        address=_get_optional_field(row, ("address",)),
        is_active=_get_optional_field(row, ("is_active", "active")),
    )


TRecord = TypeVar("TRecord")


def _parse_file_batch(
    file_paths: list[str | Path],
    *,
    parse_one: Callable[[str | Path], tuple[list[TRecord], ParsingSummary, ParsingErrorCollection]],
    batch_name: str,
) -> tuple[list[TRecord], ParsingBatchSummary, ParsingErrorCollection]:
    """Parse a deterministic file batch and aggregate records + summary + errors."""
    all_records: list[TRecord] = []
    all_errors = FileParser.create_error_collection()
    batch_summary = ParsingBatchSummary(batch_name=batch_name)
    for raw_path in file_paths:
        records, summary, errors = parse_one(raw_path)
        all_records.extend(records)
        all_errors.extend(errors.errors)
        batch_summary.add_file_summary(summary)
    return all_records, batch_summary, all_errors


def parse_products_file(
    file_path: str | Path,
) -> tuple[list[ParsedProductRecord], ParsingSummary, ParsingErrorCollection]:
    """Parse an MVP product file and return parsed records with structured outcomes."""
    summary = FileParser.create_summary(file_path)
    errors = FileParser.create_error_collection()
    _, rows = _read_rows(file_path)

    records: list[ParsedProductRecord] = []
    for row_number, row in rows:
        try:
            records.append(_build_product_record(row_number, row))
            summary.accepted_rows += 1
        except _RowValidationError as exc:
            summary.rejected_rows += 1
            errors.add(
                ParsingError(
                    row_number=row_number,
                    field_name=exc.field_name,
                    message=exc.message,
                    raw_value=exc.raw_value,
                )
            )

    return records, summary, errors


def parse_prices_file(
    file_path: str | Path,
) -> tuple[list[ParsedPriceRecord], ParsingSummary, ParsingErrorCollection]:
    """Parse an MVP price file and return parsed records with structured outcomes."""
    summary = FileParser.create_summary(file_path)
    errors = FileParser.create_error_collection()
    _, rows = _read_rows(file_path)

    records: list[ParsedPriceRecord] = []
    for row_number, row in rows:
        try:
            records.append(_build_price_record(row_number, row))
            summary.accepted_rows += 1
        except _RowValidationError as exc:
            summary.rejected_rows += 1
            errors.add(
                ParsingError(
                    row_number=row_number,
                    field_name=exc.field_name,
                    message=exc.message,
                    raw_value=exc.raw_value,
                )
            )

    return records, summary, errors


def parse_stores_file(
    file_path: str | Path,
) -> tuple[list[ParsedStoreRecord], ParsingSummary, ParsingErrorCollection]:
    """Parse an MVP store file and return parsed records with structured outcomes."""
    summary = FileParser.create_summary(file_path)
    errors = FileParser.create_error_collection()
    _, rows = _read_rows(file_path)

    records: list[ParsedStoreRecord] = []
    for row_number, row in rows:
        try:
            records.append(_build_store_record(row_number, row))
            summary.accepted_rows += 1
        except _RowValidationError as exc:
            summary.rejected_rows += 1
            errors.add(
                ParsingError(
                    row_number=row_number,
                    field_name=exc.field_name,
                    message=exc.message,
                    raw_value=exc.raw_value,
                )
            )

    return records, summary, errors


def parse_prices_file_batch(
    file_paths: list[str | Path],
) -> tuple[list[ParsedPriceRecord], ParsingBatchSummary, ParsingErrorCollection]:
    """Parse multiple price files and return one aggregate batch summary."""
    return _parse_file_batch(file_paths, parse_one=parse_prices_file, batch_name="prices")


def parse_stores_file_batch(
    file_paths: list[str | Path],
) -> tuple[list[ParsedStoreRecord], ParsingBatchSummary, ParsingErrorCollection]:
    """Parse multiple store files and return one aggregate batch summary."""
    return _parse_file_batch(file_paths, parse_one=parse_stores_file, batch_name="stores")
