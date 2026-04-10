# Module guide

This document records layer responsibilities and the current evidence-backed boundary checks for the MVP architecture.

## Layer responsibilities (finalized for MVP)

### `Modules/app`
- Owns use-case orchestration and application-facing workflows.
- May coordinate collaborators through protocols/interfaces.
- Must not own basket matching, chain ranking, or price-calculation rules.

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

## Automated guardrails

Architecture boundary checks are enforced in `tests/unit/test_architecture_boundaries.py`:

1. `Modules/app/application_service.py` remains thin and does not import concrete `Modules.engine`, `Modules.data`, or `Modules.db` modules.
2. `Modules/engine/*` does not import file/parsing modules (`csv`, `json`, `pathlib`, `sqlite3`), does not import `Modules.data`, and does not call `open()` directly.
3. `Modules/data/*` does not import `Modules.engine` and does not define comparison/ranking APIs (`compare_basket`, `rank_chains`).
4. `Modules/db/*` does not import `Modules.engine` or `Modules.data` and does not define ranking functions.

These checks are intended as lightweight drift-prevention guardrails and are deliberately narrow to avoid false positives and unnecessary refactors.

## Verified invariants and residual risk

Verified by current tests:
- App use-case layer is thin and delegating.
- Engine layer remains free from raw file parsing and direct file I/O.
- Data layer remains focused on parsing/loading rather than basket comparison.
- DB layer remains persistence-focused with no ranking orchestration logic.

Residual risk:
- AST-based guardrails validate import/function/call shape, not full semantic intent; subtle boundary drift can still occur inside otherwise valid modules.
- CLI adapter code in `Modules/app/cli.py` intentionally composes layers and accesses persistence collaborators directly for command execution, so deeper policy checks there should remain explicit and conservative.
