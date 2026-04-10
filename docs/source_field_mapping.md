# Source-to-internal field mapping (MVP)

This document defines deterministic mapping rules used by `Modules/data/parser.py` when converting retailer source rows into internal parsed records.

## 1) Store file mapping

Internal target: `ParsedStoreRecord`.

| Internal field | Accepted source fields (first match wins) | Normalization |
|---|---|---|
| `chain_code` | `chain_code`, `chain` | required, trimmed/collapsed whitespace, uppercased |
| `chain_name` | `chain_name`, `chain` | required text |
| `store_code` | `store_code`, `store` | required, trimmed/collapsed whitespace, uppercased |
| `store_name` | `store_name`, `name`, `store` | required text |
| `city` | `city` | optional text; empty -> `None` |
| `address` | `address` | optional text; empty -> `None` |
| `is_active` | `is_active`, `active` | optional text; empty -> `None` |

## 2) Price file mapping

Internal target: `ParsedPriceRecord`.

| Internal field | Accepted source fields (first match wins) | Normalization |
|---|---|---|
| `chain_code` | `chain_code`, `chain` | required, trimmed/collapsed whitespace, uppercased |
| `store_code` | `store_code`, `store` | required, trimmed/collapsed whitespace, uppercased |
| `barcode` | `barcode`, `product_barcode` | required; separators removed (`-`/spaces/etc), then validated as 8-14 digits |
| `price_text` | `price`, `price_text` | required text (stored as text in parse stage) |
| `currency` | `currency` | required, trimmed/collapsed whitespace, uppercased |
| `price_date_text` | `price_date`, `price_date_text`, `date` | required; normalized to `YYYY-MM-DD` |

Supported date formats:
- `YYYY-MM-DD`
- `YYYY/MM/DD`
- `DD/MM/YYYY`
- `YYYYMMDD`
- ISO datetime (for example `2026-04-09T10:30:00Z`), stored as date part only

## 3) Product file mapping

Internal target: `ParsedProductRecord`.

| Internal field | Accepted source fields (first match wins) | Normalization |
|---|---|---|
| `barcode` | `barcode`, `product_barcode` | required; separators removed (`-`/spaces/etc), then validated as 8-14 digits |
| `product_name` | `product_name`, `name`, `product` | required text |
| `normalized_name` | derived from `product_name` | lowercase + normalized whitespace |
| `brand` | `brand` | optional text; empty -> `None` |
| `unit_name` | `unit_name`, `unit` | optional text; empty -> `None` |

## 4) Safety behavior for malformed/missing data

- Required fields that are missing/empty reject the row with a structured parsing error.
- Invalid barcodes reject the row.
- Unsupported date formats reject the row.
- Parser continues processing remaining rows and reports accepted/rejected counts.
- Mapping and normalization remain in `Modules/data` to avoid leaking source assumptions into `Modules/engine` or `Modules/app`.
