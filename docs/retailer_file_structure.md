# Retailer file structure for downloaded transparency data

## 1) Purpose

This document explains the main retailer file families used in the Israeli supermarket transparency ecosystem and how they map into this repository’s local import/comparison flow.

It is intended to support future parsing and loading work in `Modules/data`, `Modules/db`, and `Modules/engine`.

## 2) Scope

- Focus: downloaded retailer transparency files and their conceptual role.
- Not in scope: implementation changes, parser code changes, schema changes.
- This document distinguishes between:
  - **Fact (documented):** explicitly stated in upstream/public references.
  - **Inference:** reasoned from upstream package usage patterns and naming conventions.

## 3) Retailer file families

### 3.1 Canonical families (fact)

The upstream downloader/parser ecosystem used by this project references these file type families explicitly:

- `STORE_FILE`
- `PRICE_FILE`
- `PRICE_FULL_FILE`
- `PROMO_FILE`
- `PROMO_FULL_FILE`

These names appear in the public package interfaces/documentation for `il-supermarket-scraper` and `il-supermarket-parser`.

### 3.2 Conceptual meaning (mixed: fact + inference)

- **Stores**: branch/store identity and location metadata.
- **Products**: usually derived from item-level content in price files (see inference below).
- **Prices**: item price snapshots by chain/store/time.
- **Promotions**: campaign/discount metadata linked to product identifiers.

> **Inference note:** upstream references clearly expose file families but do not fully standardize one universal cross-chain field dictionary in the same single public page. Product-level rows are commonly extracted from price-related files in practice, but exact field availability may vary per chain implementation.

## 4) Naming conventions and common patterns

## 4.1 Practical naming signals (fact)

Upstream interfaces expose file-family labels in uppercase (`STORE_FILE`, `PRICE_FILE`, etc.) and allow filtering downloads by those families.

## 4.2 Typical raw filenames/prefixes (inference)

In real dumps, filenames are often prefixed with family-like tokens such as:

- `Stores...`
- `Price...` / `PriceFull...`
- `Promo...` / `PromoFull...`

and may include chain identifiers, store IDs, and timestamps.

> **Inference note:** exact token placement and separators are chain-specific. Some chains/devices produce atypical names (including extra punctuation or duplicated separators/extensions).

## 5) Compression and packaging notes

### 5.1 Common observed packaging in ecosystem tooling (inference)

The ecosystem commonly handles raw transparency data as XML-family content, sometimes delivered as compressed artifacts (for example `.gz`, and in some workflows archive containers).

> **Inference note:** compression style is not guaranteed to be uniform across all chains and dates; downloader/parser infrastructure exists partly because chain implementations are inconsistent.

### 5.2 Parsing implication for this project (fact for architecture, inference for file quirks)

- `Modules/data` should remain responsible for format detection/normalization and parse-level validation.
- Compression/container handling should be treated as a pre-parse concern before record normalization.
- Filename oddities should not leak into business ranking logic.

## 6) Summary table (file families and internal targets)

| File family | Likely purpose | Typical example name/pattern | Relevant internal target entity | Notes |
|---|---|---|---|---|
| `STORE_FILE` | Store/branch metadata per chain | `Stores*.xml` *(inference)* | `Store`, `Chain` | Primary input for chain/store identity and availability context. |
| `PRICE_FILE` | Incremental/partial price updates | `Price*.xml` or date-stamped variants *(inference)* | `Price` (+ product identity fields where present) | Can be used for faster updates when full snapshots are not required. |
| `PRICE_FULL_FILE` | Broad/full item price snapshot | `PriceFull*.xml` *(inference)* | `Price`, `Product` | Often treated as baseline for full reloads. |
| `PROMO_FILE` | Incremental promotion updates | `Promo*.xml` *(inference)* | Promotion model (future in this repo) | Promotion ingestion is separate from base price ingestion logic. |
| `PROMO_FULL_FILE` | Full promotion snapshot | `PromoFull*.xml` *(inference)* | Promotion model (future in this repo) | Useful for complete promotion state refreshes. |

## 7) Mapping to internal project flow

This section aligns external file families to current repository terminology.

1. **Download**
   - Pull chain files into local raw storage by selected family (`STORE_FILE`, `PRICE_*`, `PROMO_*`).
2. **Parse**
   - Detect format/container, decode payload, normalize fields, validate rows.
3. **Load**
   - Persist normalized store/product/price records to local SQLite.
4. **Compare**
   - Use DB-backed entities to compute basket totals, missing items, and chain ranking.

> **Inference note:** current MVP comparison behavior in this repo is chain-level and local-first; promotion behavior is expected to be additive and should not bypass existing layer boundaries.

## 8) Known issues and ambiguities

- **Chain-specific differences (fact from upstream project context):** upstream projects continuously test because supermarket interfaces can change.
- **Filename irregularities (inference):** odd filenames, duplicated separators/extensions, and inconsistent date tokens are plausible and should be normalized defensively.
- **Compression variability (inference):** some files may arrive compressed while others are plain XML/text.
- **Conflicting references (fact):** public references span regulation pages, package docs, and community tooling; they may not always expose identical detail level for field-level schemas.

## 9) Sources and references

1. `il-supermarket-parser` (PyPI project description), including explicit file-family usage context and references to regulatory sources: https://pypi.org/project/il-supermarket-parser/
2. `il-supermarket-scraper` (PyPI project description), including configurable `ENABLED_FILE_TYPES` and reference to `file_types.py`: https://pypi.org/project/il-supermarket-scraper/
3. OpenIsraeliSupermarkets organization (upstream repositories for scraper/parser/publishing context): https://github.com/OpenIsraeliSupermarkets
4. Israel government transparency regulation landing page referenced by upstream parser docs: https://www.gov.il/he/pages/cpfta_prices_regulations
5. Nevo legal reference linked by upstream parser docs for file-definition/legal framing: https://www.nevo.co.il/law_html/law01/501_131.htm

---

### Quick confidence legend used above

- **Fact (documented):** explicitly present in linked sources.
- **Inference:** consistent with source context and ecosystem behavior, but not explicitly guaranteed in one canonical spec page.
