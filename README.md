# smart-basket

Local-first MVP scaffold for basket price comparison across retail chains.

## Current status

The repository is in active MVP development.
Core modules and unit tests exist, while several roadmap items are still open in `TODO.md`.

## Runtime and test baseline

- Target Python version: **Python 3.12**.
- CI workflow is configured to run unit tests with `actions/setup-python` using `python-version: '3.12'` in `.github/workflows/unit-tests.yml`.
- Local command used by the project for test execution:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Evidence-based compatibility statement

Current repository evidence supports the following:

1. The project is explicitly designed around Python 3.12 in project documentation (`AGENTS.md`, `docs/test_strategy.md`, and `docs/system_spec.md`).
2. CI is configured to execute tests on Python 3.12.
3. In this repository environment, tests also execute successfully on Python 3.10.

This provides a clear **Python 3.12 expectation and CI validation path**, while local execution on a given machine still depends on that machine having Python 3.12 installed.

## Offline and local-only assumptions

This MVP is intentionally local-first and offline-capable.

### In scope

- local file parsing from repository/host filesystem
- local SQLite storage
- local basket comparison logic
- deterministic local unit tests via `unittest`

### Out of scope

- backend services
- remote sync
- cloud dependencies
- API/web UI runtime assumptions
- network-required test flows

### Practical offline boundary

Repository code and tests are written to run without network access.
Dependency policy also prefers standard-library-only behavior (see `requirements.txt`, which currently states no third-party packages are required).

CI itself runs in GitHub-hosted infrastructure, but runtime behavior under test remains local/offline in design and implementation.

## Running tests locally

From repository root:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

If you want to match CI expectations exactly, run this with Python 3.12.

## Basic CLI (local MVP consumer)

Run the CLI with Python module execution:

```bash
python -m Modules.app.cli --help
```

Examples:

```bash
# load local files
python -m Modules.app.cli --db-path data/generated/smart_basket.sqlite load products tests/fixtures/parser/products_valid.csv
python -m Modules.app.cli --db-path data/generated/smart_basket.sqlite load stores <stores_file.csv>
python -m Modules.app.cli --db-path data/generated/smart_basket.sqlite load prices <prices_file.csv>

# add basket items
python -m Modules.app.cli --db-path data/generated/smart_basket.sqlite add-item 1 7290012345678 --input-type barcode --quantity 2
python -m Modules.app.cli --db-path data/generated/smart_basket.sqlite add-item 1 "milk 1l" --input-type name --quantity 1

# compare basket
python -m Modules.app.cli --db-path data/generated/smart_basket.sqlite compare 1
```
