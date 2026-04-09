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
- [ ] Implement text normalization helpers
- [ ] Implement product name normalization helpers
- [ ] Implement barcode, quantity, price, and required-field validation
- [ ] Add unit tests for utilities and validators

## 5. SQLite connection manager and schema creation
- [ ] Implement `ConnectionFactory` and `DatabaseManager`
- [ ] Implement schema creation for `products`, `chains`, `stores`, `prices`, and `basket_items`
- [ ] Create required foreign keys and indexes
- [ ] Add unit tests for schema creation and DB initialization

## 6. ProductRepository
- [ ] Implement product upsert
- [ ] Implement lookup by barcode
- [ ] Implement lookup by normalized name
- [ ] Implement retrieval by product IDs
- [ ] Add repository unit tests

## 7. ChainRepository and StoreRepository
- [ ] Implement chain upsert and lookup operations
- [ ] Implement store upsert and lookup operations
- [ ] Implement retrieval of stores by chain
- [ ] Add repository unit tests

## 8. PriceRepository
- [ ] Implement price upsert
- [ ] Implement price retrieval by product and chain
- [ ] Implement `get_prices_for_products_by_chain()`
- [ ] Implement the MVP representative price rule for a chain
- [ ] Add repository unit tests

## 9. BasketRepository
- [ ] Implement basket item persistence
- [ ] Implement basket retrieval by basket ID
- [ ] Implement basket item update and deletion
- [ ] Add repository unit tests

## 10. Parser core infrastructure
- [ ] Implement parsing models such as `ParsedProductRecord` and `ParsedPriceRecord`
- [ ] Implement `FileParser`
- [ ] Implement file format detection
- [ ] Implement parsing summary and error collection structures
- [ ] Add parser infrastructure unit tests

## 11. Product, store, and price file parsing
- [ ] Implement `parse_products_file()`
- [ ] Implement `parse_prices_file()`
- [ ] Implement `parse_stores_file()`
- [ ] Implement row normalization and invalid row handling
- [ ] Add parsing unit tests with deterministic fixtures

## 12. Data loader orchestration
- [ ] Implement `LoadJob` and `LoadResult`
- [ ] Implement `PriceDataLoader`
- [ ] Implement `load_products()`, `load_prices()`, and `load_stores()`
- [ ] Implement `replace` and `append` loading modes
- [ ] Add loader unit tests

## 13. Barcode-based product matching
- [ ] Implement direct product matching by barcode
- [ ] Mark unknown barcode items as unmatched
- [ ] Return a consistent matching result structure
- [ ] Add matching unit tests

## 14. Name-based product matching
- [ ] Implement normalized-name product matching
- [ ] Return a single match for unambiguous results
- [ ] Return candidate lists for ambiguous matches
- [ ] Mark unknown names as unmatched
- [ ] Add matching unit tests

## 15. Basket calculation
- [ ] Implement basket item validation before calculation
- [ ] Implement matched product ID collection
- [ ] Implement line price and total chain cost calculation
- [ ] Implement found item counting
- [ ] Add calculation unit tests

## 16. Missing item handling and structured result building
- [ ] Mark missing products per chain
- [ ] Implement `missing_items` collection
- [ ] Implement `is_complete_basket`
- [ ] Build `BasketLineResult`, `ChainComparisonResult`, and `BasketComparisonResult`
- [ ] Return `unmatched_items` separately
- [ ] Add unit tests

## 17. Chain ranking and comparison service
- [ ] Implement `BasketCalculator` integration into comparison flow
- [ ] Implement `BasketComparisonService`
- [ ] Implement `compare_basket()`
- [ ] Implement `rank_chains()` with complete baskets ranked before partial baskets
- [ ] Add unit tests for ranking and comparison behavior

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
- [ ] Complete `test_utils.py` *(partial: file exists, currently empty)*
- [ ] Complete `test_db.py` *(partial: file exists, currently empty)*
- [ ] Complete `test_data.py` *(partial: file exists, currently empty)*
- [ ] Complete `test_engine.py` *(partial: file exists, currently empty)*
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
