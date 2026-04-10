# Module guide

This document records layer responsibilities and the current evidence-backed boundary checks for the MVP architecture.

## Layer responsibilities (finalized for MVP)

Checked modules and tests for evidence of separation between:
- parsing (`Modules/data/parser.py`)
- DB access/persistence (`Modules/db/*`)
- business logic (`Modules/engine/*`)
- application orchestration (`Modules/app/*`)
- optional downloader integration boundaries (`Modules/data/remote_download.py`)

### `Modules/engine`
- Owns basket matching, missing-item detection, total calculations, and deterministic ranking.
- Must not perform file I/O or parse raw source files.

### `Modules/data`
- Owns local file parsing/normalization and load-flow orchestration into DB repositories.
- Must not implement basket comparison/ranking logic.

### `Modules/db`
- Owns SQLite schema, persistence, and repository query logic.
- May include approved repository selection rules (for MVP, representative chain price = minimum store price per chain/product).
- Must not implement basket ranking/matching business logic.

### `Modules/models`
- Owns entities and result DTOs shared across layers.

### `Modules/utils`
- Owns focused reusable helpers (e.g., normalization and validation).

Implemented:
- Parsing is isolated in `parser.py` with format detection, row normalization, validation, and structured parse errors.
- Optional remote downloader integration is isolated in `remote_download.py` and focused on raw-file retrieval.

Architecture boundary checks are enforced in `tests/unit/test_architecture_boundaries.py`:

Boundary note:
- Downloader responsibilities stop at local raw-file download. Import parsing/loading remains a separate flow.

### Modules/db
**Status: Partial**

These checks are intended as lightweight drift-prevention guardrails and are deliberately narrow to avoid false positives and unnecessary refactors.

## Verified invariants and residual risk

Verified by current tests:
- App use-case layer is thin and delegating.
- Engine layer remains free from raw file parsing and direct file I/O.
- Data layer remains focused on parsing/loading rather than basket comparison.
- DB layer remains persistence-focused with no ranking orchestration logic.

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
