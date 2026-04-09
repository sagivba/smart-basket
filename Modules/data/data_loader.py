"""Data loading orchestration for MVP local file ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sqlite3
from typing import Any, Literal

from Modules.data import parser
from Modules.db.repositories import DataImportRepository

LoadMode = Literal["append", "replace"]


@dataclass(slots=True)
class LoadJob:
    """Describes one deterministic data-loading operation."""

    entity: Literal["products", "prices", "stores"]
    source_path: Path
    mode: LoadMode = "append"


@dataclass(slots=True)
class LoadResult:
    """Aggregated result details for one load operation."""

    job: LoadJob
    accepted_count: int = 0
    rejected_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        """Return total rows handled by the load operation."""
        return self.accepted_count + self.rejected_count

    @property
    def success(self) -> bool:
        """Return True when no fatal errors were recorded."""
        return not self.errors


class PriceDataLoader:
    """Coordinates parser output persistence into SQLite tables."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        import_repository: DataImportRepository | None = None,
    ) -> None:
        self._connection = connection
        self._import_repository = import_repository or DataImportRepository(connection)

    def load_products(self, source_path: str | Path, mode: LoadMode = "append") -> LoadResult:
        """Load products from a source file into the products table."""
        job = LoadJob(entity="products", source_path=Path(source_path), mode=mode)
        result = LoadResult(job=job)

        parsed = self._parse_with("parse_products_file", job.source_path, result)
        if parsed is None:
            return result

        records, summary, parse_errors = parsed
        self._merge_parse_outcome(result, summary, parse_errors)

        self._validate_mode(mode)
        with self._connection:
            if mode == "replace":
                self._import_repository.replace_products()

            for record in records:
                try:
                    barcode = self._record_value(record, "barcode")
                    name = self._record_value(record, "product_name", "name")
                    normalized_name = self._record_value(record, "normalized_name")
                    brand = self._record_value(record, "brand", required=False)
                    unit_name = self._record_value(record, "unit_name", required=False)
                    self._import_repository.upsert_product(
                        barcode=barcode,
                        name=name,
                        normalized_name=normalized_name,
                        brand=brand,
                        unit_name=unit_name,
                    )
                    result.accepted_count += 1
                except (KeyError, sqlite3.DatabaseError, TypeError, ValueError) as exc:
                    result.rejected_count += 1
                    result.errors.append(str(exc))

        return result

    def load_stores(self, source_path: str | Path, mode: LoadMode = "append") -> LoadResult:
        """Load chain/store data from a source file into chains/stores tables."""
        job = LoadJob(entity="stores", source_path=Path(source_path), mode=mode)
        result = LoadResult(job=job)

        parsed = self._parse_with("parse_stores_file", job.source_path, result)
        if parsed is None:
            return result

        records, summary, parse_errors = parsed
        self._merge_parse_outcome(result, summary, parse_errors)

        self._validate_mode(mode)
        with self._connection:
            if mode == "replace":
                self._import_repository.replace_stores()

            for record in records:
                try:
                    chain_code = self._record_value(record, "chain_code")
                    chain_name = self._record_value(record, "chain_name", "chain")
                    store_code = self._record_value(record, "store_code")
                    store_name = self._record_value(record, "store_name", "name")
                    city = self._record_value(record, "city", required=False)
                    address = self._record_value(record, "address", required=False)
                    is_active = self._as_bool(self._record_value(record, "is_active", required=False), default=True)

                    self._import_repository.upsert_store_with_chain(
                        chain_code=chain_code,
                        chain_name=chain_name,
                        store_code=store_code,
                        store_name=store_name,
                        city=city,
                        address=address,
                        is_active=is_active,
                    )
                    result.accepted_count += 1
                except (KeyError, sqlite3.DatabaseError, TypeError, ValueError) as exc:
                    result.rejected_count += 1
                    result.errors.append(str(exc))

        return result

    def load_prices(self, source_path: str | Path, mode: LoadMode = "append") -> LoadResult:
        """Load product prices from a source file into the prices table."""
        job = LoadJob(entity="prices", source_path=Path(source_path), mode=mode)
        result = LoadResult(job=job)

        parsed = self._parse_with("parse_prices_file", job.source_path, result)
        if parsed is None:
            return result

        records, summary, parse_errors = parsed
        self._merge_parse_outcome(result, summary, parse_errors)

        self._validate_mode(mode)
        with self._connection:
            if mode == "replace":
                self._import_repository.replace_prices()

            for record in records:
                try:
                    barcode = self._record_value(record, "barcode")
                    chain_code = self._record_value(record, "chain_code")
                    store_code = self._record_value(record, "store_code")
                    price_text = self._record_value(record, "price_text", "price")
                    currency = self._record_value(record, "currency")
                    price_date_text = self._record_value(record, "price_date_text", "price_date")

                    self._import_repository.insert_price_by_codes(
                        barcode=barcode,
                        chain_code=chain_code,
                        store_code=store_code,
                        price=self._as_decimal(price_text),
                        currency=currency,
                        price_date=self._as_date_iso(price_date_text),
                        source_file=str(job.source_path),
                    )
                    result.accepted_count += 1
                except (KeyError, sqlite3.DatabaseError, TypeError, ValueError) as exc:
                    result.rejected_count += 1
                    result.errors.append(str(exc))

        return result

    @staticmethod
    def _validate_mode(mode: LoadMode) -> None:
        if mode not in {"append", "replace"}:
            raise ValueError(f"unsupported load mode: {mode}")

    def _parse_with(
        self,
        function_name: str,
        source_path: Path,
        result: LoadResult,
    ) -> tuple[list[Any], Any, list[Any]] | None:
        parse_fn = getattr(parser, function_name, None)
        if parse_fn is None:
            result.errors.append(f"missing parser function: {function_name}")
            return None

        try:
            raw_output = parse_fn(source_path)
        except Exception as exc:  # pragma: no cover - exercised in unit tests via behavior
            result.errors.append(f"{function_name} failed: {exc}")
            return None

        return self._normalize_parse_output(raw_output)

    @staticmethod
    def _normalize_parse_output(raw_output: Any) -> tuple[list[Any], Any, list[Any]]:
        if isinstance(raw_output, tuple):
            if len(raw_output) == 3:
                records, summary, parse_errors = raw_output
                normalized_errors = getattr(parse_errors, "errors", parse_errors)
                return list(records), summary, list(normalized_errors)
            if len(raw_output) == 2:
                records, summary = raw_output
                return list(records), summary, []
            if len(raw_output) == 1:
                return list(raw_output[0]), None, []
            return [], None, []

        if isinstance(raw_output, dict):
            records = raw_output.get("records", [])
            summary = raw_output.get("summary")
            parse_errors = raw_output.get("errors", [])
            return list(records), summary, PriceDataLoader._as_parse_error_list(parse_errors)

        records = getattr(raw_output, "records", [])
        summary = getattr(raw_output, "summary", None)
        parse_errors = getattr(raw_output, "errors", [])
        return list(records), summary, PriceDataLoader._as_parse_error_list(parse_errors)

    @staticmethod
    def _as_parse_error_list(parse_errors: Any) -> list[Any]:
        if parse_errors is None:
            return []
        if isinstance(parse_errors, list):
            return parse_errors
        if hasattr(parse_errors, "errors"):
            return list(getattr(parse_errors, "errors"))
        return list(parse_errors)

    @staticmethod
    def _merge_parse_outcome(result: LoadResult, summary: Any, parse_errors: list[Any]) -> None:
        if summary is not None:
            result.accepted_count += int(getattr(summary, "accepted_rows", 0))
            result.rejected_count += int(getattr(summary, "rejected_rows", 0))
            warnings = getattr(summary, "warnings", [])
            result.warnings.extend([str(warning) for warning in warnings])

        for parse_error in parse_errors:
            result.rejected_count += 1
            result.errors.append(str(parse_error))

    @staticmethod
    def _record_value(record: Any, *keys: str, required: bool = True) -> Any:
        for key in keys:
            if isinstance(record, dict) and key in record:
                value = record[key]
                if value is None and required:
                    raise ValueError(f"{key} is required")
                return value

            if hasattr(record, key):
                value = getattr(record, key)
                if value is None and required:
                    raise ValueError(f"{key} is required")
                return value

        if required:
            raise KeyError(f"missing required field(s): {', '.join(keys)}")
        return None

    @staticmethod
    def _as_decimal(value: str) -> str:
        try:
            return str(Decimal(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"invalid price value: {value}") from exc

    @staticmethod
    def _as_date_iso(value: str) -> str:
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"invalid date value: {value}") from exc
        return parsed.isoformat()

    @staticmethod
    def _as_bool(value: Any, *, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "y"}:
                return True
            if normalized in {"0", "false", "no", "n"}:
                return False
        raise ValueError(f"invalid boolean value: {value}")
