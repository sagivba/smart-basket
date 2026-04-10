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
- [x] Complete `test_utils.py`
- [x] Complete `test_db.py`
- [x] Complete `test_data.py`
- [x] Complete `test_engine.py`
- [x] Complete `test_app.py`
- [x] Ensure all new behavior is covered with `unittest` only

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
- [x] Document Python 3.12 compatibility expectation and verification trail
- [x] Verify the system runs fully offline
- [ ] Verify responsibilities remain cleanly separated across layers

## 25. Open MVP decisions
- [x] Representative chain price rule implemented
- [x] Ambiguous match handling policy implemented
- [x] Basket persistence policy implemented
- [x] Partial-calculation policy for unmatched items implemented
- [x] CLI scope in MVP implemented

## 26. Layer-boundary verification and architecture hardening
- [ ] Verify `app` does not implement business logic that belongs in `engine`
- [ ] Verify `engine` does not perform file I/O or direct parsing
- [ ] Verify `data` does not contain basket comparison logic
- [ ] Verify `db` does not contain business ranking/matching decisions beyond approved repository rules
- [ ] Add focused boundary tests or architecture guardrails where practical
- [ ] Document the final layer responsibilities in `docs/module_guide.md`

## 27. Download wrapper stabilization
- [ ] Stabilize `RetailChainsDownloadManager`
- [ ] Detect success based on actual files written to disk
- [ ] Distinguish `success`, `partial`, and `failed` outcomes clearly
- [ ] Fix false failure reporting when files were downloaded successfully
- [ ] Normalize enum/string handling against the external dependency
- [ ] Harden `render_report()` for partial and edge-case outputs
- [ ] Add regression tests for known wrapper bugs

## 28. Constrained download options
- [ ] Add `limit` support
- [ ] Add `when_date` support
- [ ] Add `file_types` filtering support
- [ ] Add `cleanup_before_download` support
- [ ] Validate constrained-download arguments
- [ ] Document constrained download behavior and defaults

## 29. Downloaded file inventory and filesystem handling
- [ ] Analyze the real folder structure created by the external downloader
- [ ] Respect upstream folder layout without rewriting it unnecessarily
- [ ] Add helpers for file discovery under downloaded directories
- [ ] Classify downloaded files by family (`Stores`, `Price`, `PriceFull`, `Promo`, `PromoFull`)
- [ ] Investigate unusual names such as `*.gz.xml.xml`
- [ ] Determine which naming anomalies are upstream and which are wrapper-side
- [ ] Add reporting for file counts and discovered file categories

## 30. Safe local data handling and repository hygiene
- [ ] Harden `.gitignore` for `data/raw`, generated outputs, local DBs, logs, and runtime artifacts
- [ ] Ensure `data/samples` remains versioned
- [ ] Preserve `.gitkeep` handling where needed
- [ ] Document what must never be committed
- [ ] Add a short developer note for cleaning tracked local data from git index if needed

## 31. Retailer file structure documentation
- [ ] Create `docs/retailer_file_structure.md`
- [ ] Document main retailer file families and their purpose
- [ ] Document common naming patterns and extension variants
- [ ] Document compression/container expectations (`xml`, `gz`, nested naming oddities)
- [ ] Map each file family to internal targets: stores / products / prices / promos
- [ ] Add references to external/upstream documentation
- [ ] Clearly separate confirmed facts from implementation inference

## 32. Real retailer parsing support
- [ ] Extend parsing flow for real retailer XML inputs
- [ ] Add support for compressed inputs if required by actual files
- [ ] Parse store files from real retailer downloads
- [ ] Parse price files from real retailer downloads
- [ ] Decide and document whether promo files are in MVP parse scope or post-MVP scope
- [ ] Add parsing summaries for real retailer file batches
- [ ] Add deterministic tests around representative real-file fixtures

## 33. Mapping external retailer fields to internal records
- [ ] Define mapping from retailer store files to internal store records
- [ ] Define mapping from retailer price files to internal price records
- [ ] Define mapping rules for barcodes, product names, chain codes, store codes, and dates
- [ ] Handle missing or malformed source fields safely
- [ ] Document normalization rules for imported retailer data
- [ ] Add unit tests for field mapping behavior

## 34. Download-to-parse-to-load integration
- [ ] Implement discovery flow for downloaded retailer files
- [ ] Connect discovered files into parser entry points
- [ ] Connect parsed outputs into loader flows
- [ ] Support loading from a downloaded directory tree
- [ ] Produce a unified batch import summary
- [ ] Add integration tests for `downloaded files -> parse -> load`

## 35. Real retailer import into SQLite
- [ ] Import chains from retailer data where needed
- [ ] Import stores from real retailer files
- [ ] Import prices from real retailer files
- [ ] Ensure idempotent or controlled repeated imports
- [ ] Validate `replace` versus `append` semantics for real import batches
- [ ] Add end-to-end integration tests against small real-world fixtures

## 36. Post-download operational tooling
- [ ] Add cleanup command or helper for large downloaded folders
- [ ] Add reporting for download size and file count
- [ ] Add a safe repeat-run workflow for local experimentation
- [ ] Improve `run_examples.md` for real download/import flows
- [ ] Document recommended local workflow: `download -> inspect -> parse -> load -> compare`

## 37. Promotions decision track
- [ ] Decide whether `Promo` / `PromoFull` are ignored in MVP
- [ ] If ignored, document that clearly
- [ ] If included later, define a separate post-MVP promo ingestion plan
- [ ] Keep promo support isolated from core basket comparison until explicitly enabled

## 38. Real-data comparison validation
- [ ] Validate that imported real retailer prices participate correctly in basket comparison
- [ ] Verify chain ranking still behaves correctly with partial baskets
- [ ] Verify unmatched and ambiguous items still surface correctly after real import
- [ ] Add at least one realistic end-to-end comparison scenario using imported retailer data

## 39. Documentation and developer workflow alignment
- [ ] Update `README.md` for real download/import usage
- [ ] Add links from `README.md` to retailer-file documentation
- [ ] Update `module_guide.md` if import/download boundaries changed
- [ ] Update `run_examples.md` with safe examples that do not require committing raw retailer data
- [ ] Document external dependency role and boundaries explicitly
