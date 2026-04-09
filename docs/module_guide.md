# Module Guide (implementation-aligned)

This guide reflects the **current repository state** and aligns with `docs/system_spec.md` as the source of truth. It describes what is implemented now, what is partial, what is placeholder-only, and what is missing.

## Scope and constraints (current MVP)

- **Local-First only** (no remote services).
- **Python 3.12**, **SQLite**, **unittest**.
- Layered architecture must stay strict:
  - `Modules/data`
  - `Modules/db`
  - `Modules/engine`
  - `Modules/app`
  - `Modules/models`
  - `Modules/utils`

## Dependency directions (allowed)

```text
Modules/app    -> Modules/data, Modules/engine, Modules/db (via protocols), Modules/models
Modules/data   -> Modules/utils, Modules/db (SQLite persistence), Modules/models (optional contracts)
Modules/engine -> Modules/models
Modules/db     -> Modules/models
Modules/models -> (no internal module dependencies required)
Modules/utils  -> (standard library only)
```

### Dependency rules

- `Modules/app` is orchestration-only; do not place heavy comparison logic or raw SQL here.
- `Modules/data` may parse/normalize and load into DB, but must not own basket comparison logic.
- `Modules/db` owns schema/repository persistence only; no business decisions.
- `Modules/engine` owns matching/calculation/result construction; it must not parse files directly.
- `Modules/models` defines data contracts and result models; no infrastructure logic.
- `Modules/utils` contains focused shared helpers only.

## Layer status by module

### `Modules/data`

**Responsibility**
- Parse local CSV/JSON source files.
- Normalize row fields and collect structured parsing errors.
- Orchestrate deterministic loading into SQLite tables.

**Implemented**
- `FileParser` format detection and parsing summary/error infrastructure.
- Product/price/store parsing flows with field normalization and validation.
- `PriceDataLoader` with `load_products`, `load_stores`, `load_prices`, plus append/replace handling.

**Partial**
- Loader currently writes directly with SQL in `PriceDataLoader`; repository-based persistence abstraction is not yet in place for non-basket entities.

**Placeholder-only / Missing**
- No broader import orchestration beyond current loader API.

### `Modules/db`

**Responsibility**
- SQLite connection management.
- Schema creation/index creation.
- Repository persistence APIs.

**Implemented**
- `ConnectionFactory`, `DatabaseManager`, and idempotent schema creation for products/chains/stores/prices/basket_items.
- `BasketRepository` add/get/update/delete operations.

**Partial**
- Product/chain/store/price repositories are not implemented as dedicated classes.

**Missing**
- Repository APIs expected by future engine/application flows (product lookup, chain/store lookup, representative chain pricing queries).

### `Modules/engine`

**Responsibility**
- Basket item matching.
- Price/missing detection and basket total calculations.
- Structured comparison result generation.

**Implemented**
- `BasketEngine` barcode matching helpers.
- Calculation and result-building for chain-level output (`BasketLineResult`, `ChainComparisonResult`, `BasketComparisonResult`).
- Missing-item detection and unmatched item passthrough in top-level result.

**Partial**
- Chain ranking policy from system spec (complete baskets before partial, then total price) is not implemented as a dedicated ranking workflow.
- Name-based matching behavior is not implemented.

**Missing**
- Full comparison service that integrates repository-backed product/price retrieval and ranking end-to-end.

### `Modules/app`

**Responsibility**
- Thin use-case orchestration for loading, basket item persistence, comparison invocation, and chain listing.

**Implemented**
- `ApplicationService` facade.
- `LoadPricesUseCase`, `AddBasketItemUseCase`, `CompareBasketUseCase`, `ListChainsUseCase` using protocol-based collaborators.

**Partial**
- Comparison and chain listing rely on collaborator contracts that are not fully backed by implemented DB repositories/services.

**Missing**
- Basket management use cases beyond add/compare/list (update/remove/clear/current-state retrieval).

### `Modules/models`

**Responsibility**
- Domain entities and output/result contracts shared across layers.

**Implemented**
- Entities: `Product`, `Chain`, `Store`, `Price`, `BasketItem`.
- Results/enums: `BasketLineResult`, `ChainComparisonResult`, `BasketComparisonResult`, `MatchStatus`, `AvailabilityStatus`.

**Partial**
- Validation is present, but no additional shared constants module currently exists.

### `Modules/utils`

**Responsibility**
- Focused reusable helpers for text normalization and basic validation.

**Implemented**
- Text normalization helpers (`normalize_whitespace`, `normalize_text`, `normalize_product_name`).
- Validators for barcode, quantity, price, and required text.

**Missing**
- No additional utility categories are needed for current MVP; avoid broadening this layer.

## Anti-patterns to avoid

- Putting comparison/ranking logic inside `Modules/db` or `Modules/data`.
- Parsing files directly in `Modules/engine`.
- Writing raw SQL in `Modules/app` when repository abstractions exist.
- Treating planned/future behavior as implemented in docs.
- Moving shared business rules into `Modules/utils` to bypass engine boundaries.

## Evidence baseline (code + tests)

- Current implemented behavior is evidenced by:
  - unit tests for app/data/db/engine/models/utils
  - integration tests for import flow and comparison result building
- Gaps listed above remain documented as partial/missing until matching code and tests exist.
