# Retailer file structure for downloaded transparency data

## 1. Purpose

This document provides a working reference for the downloaded retailer transparency files used by this project, so future parsing/loading tasks can make consistent decisions.

It is intentionally practical: it focuses on file-family intent, naming/packaging expectations, and mapping into this repository’s internal targets.

## 2. Scope

- In scope:
  - downloaded retailer file families used in the transparency ecosystem
  - naming and extension patterns seen in tooling and raw feeds
  - compression/container expectations for ingestion planning
  - mapping to internal targets: `stores`, `products`, `prices`, `promos`
- Out of scope:
  - implementation changes
  - schema changes
  - parser code changes

### Fact vs inference policy used in this document

- **Confirmed fact:** explicitly stated in upstream/public docs.
- **Inference:** likely conclusion based on ecosystem patterns/tool usage, but not guaranteed as a universal rule.

## 3. Retailer file families

The upstream ecosystem used by this repository explicitly references the following families:

- `STORE_FILE` (**Confirmed fact**)
- `PRICE_FILE` (**Confirmed fact**)
- `PRICE_FULL_FILE` (**Confirmed fact**)
- `PROMO_FILE` (**Confirmed fact**)
- `PROMO_FULL_FILE` (**Confirmed fact**)

### Family purpose summary

- `STORE_FILE`: branch/store identity and location metadata (**Confirmed fact/inference mix**: family exists as fact; exact field composition may vary).
- `PRICE_FILE`: incremental/partial price updates (**Inference**, based on common naming/usage semantics).
- `PRICE_FULL_FILE`: full/broader price snapshot (**Inference**, based on naming semantics).
- `PROMO_FILE`: incremental promotion updates (**Inference**, based on naming semantics).
- `PROMO_FULL_FILE`: full promotion snapshot (**Inference**, based on naming semantics).

## 4. Naming conventions and common patterns

### Common file-family tokens

- Uppercase family identifiers appear in upstream interfaces (for filtering/selection): `STORE_FILE`, `PRICE_FILE`, `PRICE_FULL_FILE`, `PROMO_FILE`, `PROMO_FULL_FILE` (**Confirmed fact**).

### Common filename patterns in raw datasets

Typical prefixes found in ecosystem discussions/tooling include:

- `Stores...`
- `Price...`
- `PriceFull...`
- `Promo...`
- `PromoFull...`

These are often combined with chain identifiers, store identifiers, and date/time fragments (**Inference**).

### Extension variants

- `.xml` is a common payload extension in this ecosystem (**Inference from tooling context**).
- Additional extension layers can appear with compression/container wrapping (for example `.xml.gz`) (**Inference**).

## 5. Compression and packaging notes

- Raw files are often XML payloads, but delivery may be plain or compressed depending on chain/source and date (**Inference**).
- Compression/container handling should be treated as pre-parse I/O work, before row normalization (**Confirmed architectural fact for this repo**).
- Expect non-uniform packaging behavior across chains; parser/loading pipelines should remain defensive (**Inference**).

## 6. Mapping to internal project flow

| Retailer file family | Internal target(s) | Flow stage | Confidence |
|---|---|---|---|
| `STORE_FILE` | `stores` (+ chain identity support) | download → parse → load | Mixed (family fact, field details vary) |
| `PRICE_FILE` | `prices` (+ product identity fields when present) | download → parse → load | Inference |
| `PRICE_FULL_FILE` | `prices` + `products` | download → parse → load | Inference |
| `PROMO_FILE` | `promos` (future model path) | download → parse → load | Inference |
| `PROMO_FULL_FILE` | `promos` (future model path) | download → parse → load | Inference |

### Internal flow alignment

1. **Download** selected families to local raw storage.
2. **Parse** with format/container detection and field normalization in `Modules/data`.
3. **Load** normalized entities to SQLite through `Modules/db` repositories.
4. **Compare** basket totals/ranking using loaded `stores`/`products`/`prices` in `Modules/engine`.

(Flow ownership above is a **Confirmed fact** from this repository’s module boundaries.)

## 7. Known issues and ambiguities

- File naming is not guaranteed to be globally uniform across chains (**Inference**).
- Full vs incremental behavior may be implied by names but not always perfectly reliable without per-chain validation (**Inference**).
- Compression/container format may vary by source and over time (**Inference**).
- Public references are distributed across package docs, legal/regulatory pages, and organization repositories; detail depth differs across sources (**Confirmed fact**).

## 8. MVP promo parsing scope decision

Decision for current MVP:
- `PROMO_FILE` and `PROMO_FULL_FILE` parsing is **post-MVP scope**.

Reasoning:
- Current MVP comparison outputs are based on base item prices only (`stores` + `prices` + optional `products` enrichment).
- Promo payload rules are materially more complex (time windows, conditional eligibility, quantity constraints) and would introduce business-rule logic outside current MVP scope.
- Keeping promo parsing out of MVP preserves clean module boundaries and deterministic offline behavior while still allowing future extension.

## 9. Sources and references

1. `il-supermarket-parser` (PyPI project page): https://pypi.org/project/il-supermarket-parser/
2. `il-supermarket-scraper` (PyPI project page): https://pypi.org/project/il-supermarket-scraper/
3. OpenIsraeliSupermarkets organization (upstream repos): https://github.com/OpenIsraeliSupermarkets
4. Israel government transparency regulation page: https://www.gov.il/he/pages/cpfta_prices_regulations
5. Nevo legal reference linked by upstream parser docs: https://www.nevo.co.il/law_html/law01/501_131.htm
