# TODO

## 1. Repository scaffold and project docs
- [x] Create the base directory structure
- [x] Add all package `__init__.py` files
- [x] Add `README.md`, `AGENTS.md`, `.env.example`, and minimal `requirements.txt`
- [x] Add `docs/system_spec.md`, `docs/module_guide.md`, and `docs/test_strategy.md`
- [x] Add `data/raw`, `data/samples`, `data/generated`, and `tests/fixtures`

## 2. Core domain entities
- [x] Implement `Product`, `Chain`, `Store`, `Price`, and `BasketItem`
- [x] Keep domain models independent from DB and business logic
- [x] Add unit tests for entity creation and basic validation

## 3. Result models and enums
- [x] Implement `BasketLineResult`, `ChainComparisonResult`, and `BasketComparisonResult`
- [x] Implement `MatchStatus` and `AvailabilityStatus`
- [x] Add shared constants needed by result models
- [x] Add unit tests for result model behavior

## 4. Text utilities and validators
- [x] Implement text normalization helpers
- [x] Implement product name normalization helpers
- [x] Implement barcode, quantity, price, and required-field validation
- [x] Add unit tests for utilities and validators

## 5. SQLite connection manager and schema creation
- [x] Implement `ConnectionFactory` and `DatabaseManager`
- [x] Implement schema creation for `products`, `chains`, `stores`, `prices`, and `basket_items`
- [x] Create required foreign keys and indexes
- [x] Add unit tests for schema creation and DB initialization

## 6. ProductRepository
- [x] Implement product upsert
- [x] Implement lookup by barcode
- [x] Implement lookup by normalized name
- [x] Implement retrieval by product IDs
- [x] Add repository unit tests

## 7. ChainRepository and StoreRepository
- [x] Implement chain upsert and lookup operations
- [x] Implement store upsert and lookup operations
- [x] Implement retrieval of stores by chain
- [x] Add repository unit tests

## 8. PriceRepository
- [x] Implement price upsert
- [x] Implement price retrieval by product and chain
- [x] Implement `get_prices_for_products_by_chain()`
- [x] Implement the MVP representative price rule for a chain
- [x] Add repository unit tests

## 9. BasketRepository
- [x] Implement basket item persistence
- [x] Implement basket retrieval by basket ID
- [x] Implement basket item update and deletion
- [x] Add repository unit tests

## 10. Parser core infrastructure
- [x] Implement parsing models such as `ParsedProductRecord` and `ParsedPriceRecord`
- [x] Implement `FileParser`
- [x] Implement file format detection
- [x] Implement parsing summary and error collection structures
- [x] Add parser infrastructure unit tests

## 11. Product, store, and price file parsing
- [x] Implement `parse_products_file()`
- [x] Implement `parse_prices_file()`
- [x] Implement `parse_stores_file()`
- [x] Implement row normalization and invalid row handling *(for product/price parsing flows)*
- [x] Add parsing unit tests with deterministic fixtures

## 12. Data loader orchestration
- [x] Implement `LoadJob` and `LoadResult`
- [x] Implement `PriceDataLoader`
- [x] Implement `load_products()`, `load_prices()`, and `load_stores()`
- [x] Implement `replace` and `append` loading modes
- [x] Add loader unit tests

## 13. Barcode-based product matching
- [x] Implement direct product matching by barcode *(covered by unit tests in `tests/unit/test_engine.py`)*
- [x] Mark unknown barcode items as unmatched *(covered by unit tests in `tests/unit/test_engine.py`)*
- [x] Return a consistent matching result structure *(covered by unit tests in `tests/unit/test_engine.py`)*
- [x] Add matching unit tests

## 14. Name-based product matching
- [x] Implement normalized-name product matching *(covered by unit tests in `tests/unit/test_engine.py`)*
- [x] Return a single match for unambiguous results *(covered by unit tests in `tests/unit/test_engine.py`)*
- [x] Return candidate lists for ambiguous matches *(covered by unit tests in `tests/unit/test_engine.py`)*
- [x] Mark unknown names as unmatched *(covered by unit tests in `tests/unit/test_engine.py`)*
- [x] Add matching unit tests

## 15. Basket calculation
- [x] Implement basket item validation before calculation
- [x] Implement matched product ID collection
- [x] Implement line price and total chain cost calculation
- [x] Implement found item counting
- [x] Add calculation unit tests

## 16. Missing item handling and structured result building
- [x] Mark missing products per chain
- [x] Implement `missing_items` collection
- [x] Implement `is_complete_basket`
- [x] Build `BasketLineResult`, `ChainComparisonResult`, and `BasketComparisonResult`
- [x] Return `unmatched_items` separately
- [x] Add unit tests

## 17. Chain ranking and comparison service
- [x] Implement `BasketCalculator` integration into comparison flow
- [x] Implement `BasketComparisonService`
- [x] Implement `compare_basket()`
- [x] Implement `rank_chains()` with complete baskets ranked before partial baskets
- [x] Add unit tests for ranking and comparison behavior

## 18. Application service and use cases
- [x] Implement `ApplicationService`
- [x] Implement `LoadPricesUseCase`
- [x] Implement `AddBasketItemUseCase`
- [x] Implement `CompareBasketUseCase`
- [x] Implement `ListChainsUseCase`
- [x] Add application-layer unit tests

## 19. Basket management at application level
- [x] Implement basket item addition
- [x] Implement basket item quantity update
- [x] Implement basket item removal
- [x] Implement basket clearing
- [x] Implement current basket state retrieval
- [x] Add unit tests

## 20. Basic CLI
- [x] Create a basic CLI entry point
- [x] Add commands for data loading, basket item addition, and basket comparison
- [x] Implement text output for comparison results, missing items, and unmatched items
- [x] Implement user-friendly error messages
- [x] Add CLI-level tests if applicable

## 21. Unit tests by module
- [x] Complete `test_models.py`
- [x] Complete `test_utils.py` *(text utility coverage added)*
- [x] Complete `test_db.py` *(BasketRepository + ChainRepository + StoreRepository coverage added)*
- [x] Complete `test_data.py` *(parser infrastructure coverage added)*
- [x] Complete `test_engine.py` *(engine result-building and validation paths covered)*
- [x] Complete `test_app.py` *(application-layer orchestration coverage added)*
- [x] Ensure all new behavior is covered with `unittest` only *(evidence: dedicated unit tests now cover engine matching paths, basket repository update guardrails, and CLI name-based matching in addition to existing repository/engine/app/integration coverage; full suite runs via `python -m unittest discover` without pytest)*

## 22. Integration tests
- [x] Implement `test_import_flow.py`
- [x] Implement `test_basket_comparison.py`
- [x] Add an end-to-end file-to-database loading scenario
- [x] Add an end-to-end basket comparison scenario
- [x] Add scenarios for missing items and unmatched items

## 23. Fixtures and sample data
- [x] Create small deterministic product fixtures
- [x] Create small deterministic store fixtures
- [x] Create small deterministic price fixtures
- [x] Create parser fixtures
- [x] Create integration test fixtures

## 24. Documentation alignment and project hardening
- [x] Update `README.md` with installation, run, and test instructions
- [x] Update `module_guide.md` with layer boundaries and dependencies
- [x] Update `test_strategy.md` with testing patterns and execution guidance
- [x] Add GitHub Actions workflow to run `unittest` discovery on `push` and `pull_request`
- [x] Document Python 3.12 compatibility expectation and verification trail *(README + test-strategy now document CI target, local test command, and evidence boundaries without over-claiming runtime guarantees)*
- [x] Verify the system runs fully offline *(evidence: `tests/unit/test_offline_constraints.py` guardrails + `tests/integration/test_offline_bootstrap.py` executes load/add-item/compare while `socket.create_connection` and `socket.socket.connect` are patched to fail if any network access is attempted)*
- [x] Verify responsibilities remain cleanly separated across layers *(implemented: `PriceDataLoader` now delegates store and price persistence through `DataImportRepository` methods (`upsert_store_with_chain`, `insert_price_by_codes`) and boundary-focused unit tests verify delegation for products/stores/prices without SQL-capable connections.)*

## 25. Open MVP decisions
- [x] Representative chain price rule — **implemented**: repository queries pick the minimum store price per chain/product (deterministic tie-break), with unit-test coverage for single-price and multi-product map behavior.
- [ ] Ambiguous match handling policy — **partial**: engine and CLI mark ambiguous name matches without auto-selecting a product and persist `match_status="ambiguous"` with `product_id=NULL`; candidate lists exist in engine match output but are not carried through persisted basket/app-level result contracts.
- [x] Basket persistence policy — **implemented**: basket items are persisted in SQLite (`basket_items` schema + repository CRUD), and application/CLI flows read and write persisted basket state by `basket_id`.
- [x] Partial-calculation policy for unmatched items — **implemented**: unmatched inputs are excluded from chain total calculations, returned separately as `unmatched_items`, and missing-per-chain reporting stays independent.
- [x] CLI scope in MVP — **implemented**: a basic CLI entry point (`load`, `add-item`, `compare`) is present and covered by dedicated unit/integration tests.
