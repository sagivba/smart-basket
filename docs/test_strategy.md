# Test Strategy

## 1. Purpose

This document defines the testing strategy for the smart-basket project.

The goal of the test suite is to ensure that:
- core domain behavior is correct
- module boundaries remain clean
- changes are safe to implement incrementally
- all tests run locally and deterministically
- the repository remains friendly to AI-assisted development

The project is local-first, uses Python 3.12, SQLite, and `unittest` only. No test should require network access or external services.

## 2. Testing Principles

### 2.1 Use `unittest` only
The project standard is `unittest` only.
`pytest` must not be introduced.

### 2.2 Prefer isolated tests
Each central component should be testable in isolation.
Business logic must not be hidden inside DB access or parsing code, and tests should reflect that separation.

### 2.3 Deterministic execution
Tests must be stable, repeatable, and runnable offline.
Avoid dependency on internet access, live data, environment-specific state, or current time unless injected explicitly.

### 2.4 Small and focused tests
Tests should be short, readable, and behavior-oriented.
A failing test should identify one clear regression.

### 2.5 Tests are mandatory for change
Every code change must include relevant tests.
Every bug fix must include a reproducing test.
Every new capability must include at least one unit test, and an integration test when the behavior crosses module boundaries.

## 3. Test Levels

### 3.1 Unit tests
Unit tests validate a single module or class in isolation.

They should cover:
- domain entities and result models
- text utilities and validators
- repositories with temporary SQLite databases
- parser behavior with small deterministic fixtures
- engine matching, calculation, missing-item handling, and ranking
- application-layer orchestration and use cases

### 3.2 Integration tests
Integration tests validate end-to-end flows across layers.

They should cover at minimum:
- file import into SQLite
- basket construction and comparison
- retrieval of products and prices through the DB layer
- full comparison output including missing items and unmatched items

### 3.3 Out of scope at this stage
The MVP excludes server APIs, cloud services, and web UI.
Tests should not assume backend services or browser-level behavior.

## 4. Repository Test Layout

Recommended test layout:

```text
tests/
  __init__.py
  fixtures/
    .gitkeep
  unit/
    __init__.py
    test_app.py
    test_data.py
    test_db.py
    test_engine.py
    test_models.py
    test_utils.py
  integration/
    __init__.py
    test_import_flow.py
    test_basket_comparison.py
```

## 5. Naming Conventions

### 5.1 Test files
- file names must start with `test_`

Examples:
- `test_models.py`
- `test_engine.py`
- `test_import_flow.py`

### 5.2 Test classes
- class names should start with `Test`

Examples:
- `TestProductEntity`
- `TestBasketComparisonService`

### 5.3 Test methods
- method names should describe expected behavior clearly

Examples:
- `test_should_match_product_by_barcode`
- `test_should_mark_missing_item_when_price_not_found`
- `test_should_rank_complete_baskets_before_partial_baskets`

## 6. Coverage by Module

### 6.1 `Modules/models`
Test:
- entity construction
- trimming and normalization behavior if implemented in models
- validation failures for invalid required fields
- result model correctness
- enums and shared constants behavior

Target coverage includes:
- `Product`, `Chain`, `Store`, `Price`, `BasketItem`
- `BasketLineResult`, `ChainComparisonResult`, `BasketComparisonResult`
- `MatchStatus`, `AvailabilityStatus`

### 6.2 `Modules/utils`
Test:
- text normalization
- product name normalization
- barcode validation
- quantity validation
- price validation
- required-field validation

### 6.3 `Modules/db`
Test:
- SQLite connection creation
- schema creation
- foreign keys and indexes
- repository upsert operations
- lookup by barcode and normalized name
- representative chain price rule
- basket persistence behavior when implemented

### 6.4 `Modules/data`
Test:
- parsing models
- file format detection
- parsing summaries and invalid row collection
- product, price, and store file parsing
- loader orchestration
- `replace` and `append` load modes

### 6.5 `Modules/engine`
Test:
- barcode matching
- normalized-name matching
- ambiguous-name handling
- unmatched-item handling
- basket calculation
- missing-item handling
- result object construction
- ranking behavior
- comparison service orchestration

### 6.6 `Modules/app`
Test:
- application service orchestration
- loading use cases
- basket item add/update/remove/clear behavior
- compare-basket use case
- current basket state retrieval
- list-chains use case

## 7. Fixtures Strategy

Fixtures must be:
- small
- deterministic
- version-controlled
- easy to read
- focused on one scenario each

### 7.1 Fixture categories
Keep fixtures for:
- products
- stores
- prices
- parser input files
- integration scenarios

### 7.2 SQLite fixtures
Use temporary SQLite databases for DB and integration tests.
Each test should create its own isolated DB state and clean up automatically.
This avoids cross-test leakage and supports reproducibility.

### 7.3 Anti-patterns
Do not use:
- live retailer files from uncontrolled sources
- real-time network downloads
- mutable shared fixture databases
- hidden dependencies on machine-specific paths or locale settings

## 8. Core Test Scenarios

### 8.1 Domain entities
- create valid `Product`, `Chain`, `Store`, `Price`, `BasketItem`
- reject or flag invalid required values
- preserve expected typed values
- verify equality or representation behavior if defined

### 8.2 Parsing
- parse valid product file
- parse valid price file
- parse valid store file
- collect invalid rows without crashing the whole file load
- return parsing summary with accepted and rejected counts

### 8.3 Loading
- load parsed records into SQLite
- verify `replace` mode clears and reloads expected tables
- verify `append` mode preserves existing valid rows where intended
- verify load result summary

### 8.4 Repositories
- upsert product
- lookup product by barcode
- lookup product by normalized name
- retrieve prices for products by chain
- apply representative chain price rule consistently
- persist and retrieve basket items when basket persistence is enabled

### 8.5 Basket engine
- match by exact barcode
- match by normalized name
- return multiple candidates for ambiguous name matches
- mark unknown items as unmatched
- calculate line totals by quantity
- mark missing products per chain
- build structured result models
- rank complete baskets before partial baskets
- keep unmatched items separate from priced results

### 8.6 Application layer
- orchestrate load flow correctly
- manage basket state correctly
- call engine services with expected inputs
- return stable response structures for future CLI consumers

### 8.7 Integration flows
- import sample files into SQLite and verify row availability
- compare a basket against multiple chains
- verify missing-item reporting
- verify unmatched-item reporting
- verify deterministic ordering of ranked results

## 9. Failure Policy

When a defect is found:
1. add a failing test that reproduces the problem
2. implement the fix
3. rerun the relevant unit and integration tests
4. keep the regression test in the suite

## 10. Execution

### 10.1 Run all tests
```bash
python -m unittest discover -s tests -p "test_*.py"
```

### 10.2 Run unit tests only
```bash
python -m unittest discover -s tests/unit -p "test_*.py"
```

### 10.3 Run integration tests only
```bash
python -m unittest discover -s tests/integration -p "test_*.py"
```

### 10.4 Run one test module
```bash
python -m unittest tests.unit.test_models
```

### 10.5 Run one test class
```bash
python -m unittest tests.unit.test_models.TestProductEntity
```

### 10.6 Run one test method
```bash
python -m unittest tests.unit.test_models.TestProductEntity.test_should_trim_fields
```

## 11. CI Expectations

The CI pipeline should:
- install Python 3.12
- install project dependencies
- run the full `unittest` suite
- fail the build on any test failure

Minimum expected CI command:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## 12. Quality Gates

A change is considered acceptable only if:
- the relevant tests were added or updated
- all tests pass locally
- the change does not introduce non-deterministic behavior
- module boundaries remain clean
- no external service dependency was added to the test flow

## 13. Maintenance Rules

- Keep tests close to the behavior they verify.
- Prefer adding new focused tests over expanding one large test method.
- Refactor tests when readability drops, but do not remove regression coverage.
- Avoid over-mocking when a temporary SQLite database gives a clearer and more realistic test.
- Keep fixtures intentionally small so failures remain easy to diagnose.

## 14. Summary

The smart-basket test strategy is based on deterministic local execution, strict use of `unittest`, clear separation between unit and integration coverage, and incremental safety for AI-assisted development.

This strategy supports t
