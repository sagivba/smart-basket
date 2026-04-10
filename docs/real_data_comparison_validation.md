# Real-data comparison validation (Task 38)

Validated with deterministic imported retailer fixtures (`tests/fixtures/integration/real_import_*.csv`) and integration flow in `tests/integration/test_real_data_comparison_validation.py`.

## Validated behaviors

- Imported retailer stores/products/prices are consumed by basket comparison after downloaded-tree import.
- Chain ranking remains two-stage:
  1. complete baskets first
  2. partial baskets second
  3. lower total inside each group
- Representative chain price remains the minimum product price across chain stores.
- Ambiguous name matches and unmatched inputs remain excluded from price totals and are surfaced under `unmatched_items`.
- Missing products per chain remain visible through `missing_items` and missing basket lines.

## Remaining limitations

- Validation scope is single-currency (`ILS`) and one import date.
- Name matching is still exact normalized-string matching; no advanced NLP/fuzzy behavior is included.
- Scenario coverage is intentionally small and deterministic for MVP correctness, not for performance or large catalogs.
