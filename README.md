# smart-basket

Local-first MVP for comparing basket costs across retail chains using local files, local SQLite, and deterministic `unittest` coverage.

## Project constraints (current baseline)

- **Local-First only**: no backend, no remote sync, no cloud dependency in runtime flows.
- **Python 3.12**: the documented and CI target runtime for this repository.
- **SQLite only**: persistence layer is implemented with Python `sqlite3` and local database files.
- **`unittest` only**: test suite is implemented and run with standard-library `unittest`.
- **Layered architecture preserved**:
  - `Modules/data`
  - `Modules/db`
  - `Modules/engine`
  - `Modules/app`
  - `Modules/models`
  - `Modules/utils`

Source-of-truth behavior is defined in `docs/system_spec.md`.

---

## Implementation status (evidence-based)

Status labels used here:
- **Implemented**: code exists and is covered by tests.
- **Partial**: some behavior exists, but full target flow is not complete.
- **Placeholder-only**: scaffolding or intended structure exists, but practical behavior is minimal.
- **Missing**: not implemented yet.

### Implemented

- Core entities and result models in `Modules/models` with unit coverage.
- Text normalization and input validators in `Modules/utils` with unit coverage.
- SQLite connection factory, schema creation, and database manager in `Modules/db.database` with unit coverage.
- `BasketRepository` CRUD-style persistence in `Modules/db.repositories` with unit coverage.
- Parser infrastructure and product/store/price parsing in `Modules/data.parser` with unit coverage.
- Local data-loading orchestration (`LoadJob`, `LoadResult`, `PriceDataLoader`) in `Modules/data.data_loader` with unit coverage.
- Engine result-building logic for chain-level basket outputs in `Modules/engine.basket_engine` with unit + integration coverage.
- Application-layer orchestration (`ApplicationService` and use-cases) in `Modules/app.application_service` with unit coverage.
- Integration tests for import flow and basket comparison result-building.

### Partial

- Basket matching/comparison engine capabilities are present, but full comparison-service/ranking orchestration described in planning docs is not fully complete yet.
- Repository coverage and implementations are complete for basket items, while broader product/chain/store/price repository interfaces remain incomplete.
- App-layer basket lifecycle beyond item addition (update/remove/clear/full state flow) is still incomplete.

### Placeholder-only

- Repository/module layout for the full MVP roadmap exists and is documented, but some planned components are intentionally still skeletal relative to full scope.

### Missing

- CLI entry point and user-facing commands are **not implemented** yet.
- No web UI, no backend/API, no auth/user management.
- No remote synchronization.

---

## Repository structure

```text
.
├── Modules/
│   ├── app/
│   ├── data/
│   ├── db/
│   ├── engine/
│   ├── models/
│   └── utils/
├── docs/
├── tests/
│   ├── fixtures/
│   ├── integration/
│   └── unit/
├── data/
│   ├── generated/
│   ├── raw/
│   └── samples/
├── README.md
├── TODO.md
└── requirements.txt
```

---

## Installation

### 1) Use Python 3.12

```bash
python3.12 --version
```

If your system maps `python` to 3.12 already:

```bash
python --version
```

### 2) Create a virtual environment (recommended)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

This repository keeps dependencies minimal. It currently includes `il-supermarket-scraper` for the optional raw transparency-file downloader integration.

```bash
python -m pip install -r requirements.txt
```

---

## Run / usage (current state)

A basic CLI entry point is available via `python -m Modules.app.cli`.

Current usage is module-driven (import/use in Python) and test-driven. The most reliable executable flows today are:

For copy-paste CLI commands against repository fixtures, see `docs/run_examples.md`.

1. Data import flow (integration-tested).
2. Basket comparison result-building flow (integration-tested).
3. Application service/use-case orchestration (unit-tested).

### Run the integration flows directly via unittest

```bash
python -m unittest tests.integration.test_import_flow -v
python -m unittest tests.integration.test_basket_comparison -v
```

### Run all tests (recommended)

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## Testing policy

- Framework: **`unittest` only**.
- Tests are local and deterministic.
- No network-required test flows.
- See `docs/test_strategy.md` for conventions and scope.

---

## What this README intentionally does not claim

To keep documentation accurate, this README does **not** claim:
- a finished CLI,
- completed end-to-end comparison-service orchestration beyond what tests currently verify,
- any backend/API/web runtime,
- any non-local execution dependency.


## Repository hygiene for local data

To keep the repository safe and reviewable, never commit:
- real downloaded retailer files under `data/raw/`
- generated outputs under `data/generated/`
- local SQLite database files and SQLite runtime sidecar files (`*.db`, `*.sqlite*`, `*-wal`, `*-shm`, `*-journal`)
- local logs and runtime artifacts (`logs/`, `*.log`, `*.pid`, temp files)

`data/samples/` is intentionally versioned for deterministic tests and examples.

If local data was already tracked in Git before ignore rules were added, remove it from the index (without deleting your local files):

```bash
git rm -r --cached data/raw data/generated
git rm --cached *.db *.sqlite *.sqlite3
git commit -m "chore: stop tracking local runtime data"
```


## Third-party attribution

This repository includes an **optional** raw-download integration that depends on:

- `il-supermarket-scraper` from OpenIsraeliSupermarkets / `israeli-supermarket-scarpers`
- OpenIsraeliSupermarkets / `israeli-supermarket-parsers`

The current integration uses the scraper package to download raw supermarket transparency files for selected chains into local folders. Parsing/loading downloaded XML/GZ files into this project's SQLite schema is a **separate step** and is not part of the downloader capability itself.

### Licensing note (third-party dependency)

The upstream OpenIsraeliSupermarkets packages referenced above are distributed under a custom non-commercial license model with attribution requirements. This project does not vendor that source code; it only integrates via external package dependency, and users should review upstream license terms before commercial use.
