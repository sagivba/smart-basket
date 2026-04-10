# Module guide

This document records a **narrow architecture audit** against `docs/system_spec.md` section 3.6 and section 4 (layered responsibilities).

## Audit scope and method

Checked modules and tests for evidence of separation between:
- parsing (`Modules/data/parser.py`)
- DB access/persistence (`Modules/db/*`)
- business logic (`Modules/engine/*`)
- application orchestration (`Modules/app/*`)
- optional downloader integration boundaries (`Modules/data/remote_download.py`)

Evidence was taken from implementation files and current `unittest` coverage only.

## Classification legend

- **Implemented**: responsibility is present and evidence-backed in code and tests.
- **Partial**: responsibility exists but boundaries are mixed or evidence is incomplete.
- **Placeholder-only**: module/file exists but does not yet implement required behavior.
- **Missing**: expected behavior is absent.

## Layer audit status (current)

### Modules/data
**Status: Partial**

Implemented:
- Parsing is isolated in `parser.py` with format detection, row normalization, validation, and structured parse errors.
- Optional remote downloader integration is isolated in `remote_download.py` and focused on raw-file retrieval.

Boundary concern:
- `PriceDataLoader` writes directly to SQLite and performs SQL lookups/upserts (`INSERT`, `DELETE`, `SELECT`) instead of delegating persistence to DB repositories.
- This conflicts with the system spec expectation that DB layer owns persistence/query logic while data layer passes cleaned records forward.

Boundary note:
- Downloader responsibilities stop at local raw-file download. Import parsing/loading remains a separate flow.

### Modules/db
**Status: Partial**

Implemented:
- SQLite connection management and schema creation are implemented in `database.py`.
- `BasketRepository` persistence methods are implemented and unit-tested.

Missing/partial:
- Repositories for products/chains/stores/prices are not implemented yet, leaving data loading to execute SQL directly from data layer.

### Modules/engine
**Status: Partial**

Implemented:
- Basket result-building logic (line construction, totals, missing tracking, unmatched passthrough) is implemented and tested.
- Engine does not read files directly.

Missing/partial:
- Full comparison/ranking service behavior in TODO section 17 is still not complete.

### Modules/app
**Status: Implemented (thin orchestration), with downstream dependency gaps**

Implemented:
- Use cases and `ApplicationService` delegate to collaborators via protocols and stay thin.
- No direct SQL or raw parsing logic is present.

Caveat:
- Because some lower-layer capabilities are partial, app behavior depends on placeholders/protocol stubs for parts of the full MVP flow.

### Modules/models
**Status: Implemented**

Implemented:
- Entities and result models are defined in dedicated model modules.
- Models remain infrastructure-agnostic.

### Modules/utils
**Status: Implemented**

Implemented:
- Text normalization and validation helpers are isolated and used by parsing/validation flows.

## External dependency boundary summary

- `il-supermarket-scraper` is an optional dependency used by the data-layer downloader only.
- Import (`load ...`), DB persistence, and engine comparison are separate local flows.
- Offline/local determinism requirements for tests still apply.

## Consolidated separation verdict

**Overall verdict: Partial**.

Clean separations are present for:
- engine vs file parsing,
- app vs SQL/parsing,
- models/utils vs infrastructure,
- downloader vs importer/comparison logic.

A clear, evidence-backed boundary violation remains:
- data layer currently contains direct persistence/query SQL that should reside in DB repositories.

No broad refactor is included in this audit update.
