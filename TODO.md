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
- [ ] Add shared constants needed by result models
- [x] Add unit tests for result model behavior

## 4. Text utilities and validators
- [x] Implement text normalization helpers
- [x] Implement product name normalization helpers
- [ ] Implement barcode, quantity, price, and required-field validation
- [ ] Add unit tests for utilities and validators

## 5. SQLite connection manager and schema creation
- [x] Implement `ConnectionFactory` and `DatabaseManager`
- [x] Implement schema creation for `products`, `chains`, `stores`, `prices`, and `basket_items`
- [x] Create required foreign keys and indexes
- [x] Add unit tests for schema creation and DB initialization

## 6. ProductRepository
- [ ] Implement product upsert
- [ ] Implement lookup by barcode
- [ ] Implement lookup by normalized name
- [ ] Implement retrieval by product IDs
- [x] Add repository unit tests

## 7. ChainRepository and StoreRepository
- [ ] Implement chain upsert and lookup operations
- [ ] Implement store upsert and lookup operations
- [ ] Implement retrieval of stores by chain
- [x] Add repository unit tests

## 8. PriceRepository
- [ ] Implement price upsert
- [ ] Implement price retrieval by product and chain
- [ ] Implement `get_prices_for_products_by_chain()`
- [ ] Implement the MVP representative price rule for a chain
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
- [ ] Implement `parse_stores_file()`
- [x] Implement row normalization and invalid row handling *(for product/price parsing flows)*
- [x] Add parsing unit tests with deterministic fixtures

## 12. Data loader orchestration
- [x] Implement `LoadJob` and `LoadResult`
- [x] Implement `PriceDataLoader`
- [x] Implement `load_products()`, `load_prices()`, and `load_stores()`
- [x] Implement `replace` and `append` loading modes
- [x] Add loader unit tests

## 13. Barcode-based product matching
- [x] Implement direct product matching by barcode
- [x] Mark unknown barcode items as unmatched
- [x] Return a consistent matching result structure
- [x] Add matching unit tests

## 14. Name-based product matching
- [ ] Implement normalized-name product matching
- [ ] Return a single match for unambiguous results
- [ ] Return candidate lists for ambiguous matches
- [ ] Mark unknown names as unmatched
- [ ] Add matching unit tests

## 15. Basket calculation
- [x] Implement basket item validation before calculation
- [x] Implement matched product ID collection
- [x] Implement line price and total chain cost calculation
- [x] Implement found item counting
- [x] Add calculation unit tests

## 16. Missing item handling and structured result building
- [ ] Mark missing products per chain
- [ ] Implement `missing_items` collection
- [ ] Implement `is_complete_basket`
- [ ] Build `BasketLineResult`, `ChainComparisonResult`, and `BasketComparisonResult`
- [ ] Return `unmatched_items` separately
- [ ] Add unit tests

## 17. Chain ranking and comparison service
- [x] Implement `BasketCalculator` integration into comparison flow
- [x] Implement `BasketComparisonService`
- [x] Implement `compare_basket()`
- [x] Implement `rank_chains()` with complete baskets ranked before partial baskets
- [x] Add unit tests for ranking and comparison behavior

## 18. Application service and use cases
- [ ] Implement `ApplicationService`
- [ ] Implement `LoadPricesUseCase`
- [ ] Implement `AddBasketItemUseCase`
- [ ] Implement `CompareBasketUseCase`
- [ ] Implement `ListChainsUseCase`
- [ ] Add application-layer unit tests

## 19. Basket management at application level
- [ ] Implement basket item addition
- [ ] Implement basket item quantity update
- [ ] Implement basket item removal
- [ ] Implement basket clearing
- [ ] Implement current basket state retrieval
- [ ] Add unit tests

## 20. Basic CLI
- [ ] Create a basic CLI entry point
- [ ] Add commands for data loading, basket item addition, and basket comparison
- [ ] Implement text output for comparison results, missing items, and unmatched items
- [ ] Implement user-friendly error messages
- [ ] Add CLI-level tests if applicable

## 21. Unit tests by module
- [x] Complete `test_models.py`
- [x] Complete `test_utils.py` *(text utility coverage added)*
- [x] Complete `test_db.py` *(BasketRepository coverage added)*
- [x] Complete `test_data.py` *(parser infrastructure coverage added)*
- [x] Complete `test_engine.py` *(barcode matching coverage added)*
- [ ] Complete `test_app.py` *(partial: file exists, currently empty)*
- [ ] Ensure all new behavior is covered with `unittest` only

## 22. Integration tests
- [ ] Implement `test_import_flow.py` *(partial: scaffold file now exists with placeholder only)*
- [ ] Implement `test_basket_comparison.py` *(partial: scaffold file now exists with placeholder only)*
- [ ] Add an end-to-end file-to-database loading scenario
- [ ] Add an end-to-end basket comparison scenario
- [ ] Add scenarios for missing items and unmatched items

## 23. Fixtures and sample data
- [ ] Create small deterministic product fixtures
- [ ] Create small deterministic store fixtures
- [ ] Create small deterministic price fixtures
- [ ] Create parser fixtures
- [ ] Create integration test fixtures

## 24. Documentation alignment and project hardening
- [ ] Update `README.md` with installation, run, and test instructions
- [ ] Update `module_guide.md` with layer boundaries and dependencies
- [ ] Update `test_strategy.md` with testing patterns and execution guidance
- [x] Add GitHub Actions workflow to run `unittest` discovery on `push` and `pull_request`
- [ ] Verify Python 3.12 compatibility
- [ ] Verify the system runs fully offline
- [ ] Verify responsibilities remain cleanly separated across layers

## 25. Open MVP decisions
- [ ] Finalize the representative chain price rule
- [ ] Finalize the ambiguous match handling policy
- [ ] Finalize whether the basket is memory-only or also persisted
- [ ] Finalize the partial-calculation policy for unmatched items
- [ ] Finalize whether the CLI is part of MVP or immediately after MVP
