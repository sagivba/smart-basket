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
- Optional retailer transparency-file downloader integration through `Modules/data/remote_download.py`.

### Partial

- Basket matching/comparison engine capabilities are present, but full comparison-service/ranking orchestration described in planning docs is not fully complete yet.
- Repository coverage and implementations are complete for basket items, while broader product/chain/store/price repository interfaces remain incomplete.
- App-layer basket lifecycle beyond item addition (update/remove/clear/full state flow) is still incomplete.

### Placeholder-only

- Repository/module layout for the full MVP roadmap exists and is documented, but some planned components are intentionally still skeletal relative to full scope.

### Missing

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

This repository keeps dependencies minimal. It currently includes `il-supermarket-scraper` for **optional** raw transparency-file downloading.

```bash
python -m pip install -r requirements.txt
```

---

## Real local workflow (download -> import -> compare)

Use this sequence for realistic local development:

1. **(Optional) Download raw retailer transparency files** into `data/raw/downloads/` using the Python API.
2. **Import local source files** into SQLite (`products`, `stores`, `prices`) using `python -m Modules.app.cli load ...`.
3. **Build basket state** with `add-item` commands.
4. **Run comparison** with `python -m Modules.app.cli compare <basket_id>`.

For copy-paste command examples, see `docs/run_examples.md`.

For retailer-file details (supported chains, file categories, hygiene, and boundaries), see `docs/retailer_files.md`.

### Raw-data hygiene (important)

- Raw retailer files under `data/raw/` are local working inputs and are **not meant to be committed**.
- `.gitignore` already excludes `data/raw/*` while preserving `data/raw/.gitkeep`.
- Keep raw downloads on your machine only; commit deterministic fixtures/samples instead.

---

## Run / usage (current state)

A basic CLI entry point is available via `python -m Modules.app.cli`.

Current CLI commands include:
- `load` for importing local products/stores/prices files.
- `add-item` for adding basket items.
- `compare` for chain-level comparison output.

> Note: retailer downloading is currently available through Python API collaborators (not a dedicated CLI command).

### Run integration flows directly via unittest

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

## External dependency boundary (retailer downloader)

This repository includes an **optional** raw-download integration that depends on:

- `il-supermarket-scraper` from OpenIsraeliSupermarkets / `israeli-supermarket-scarpers`
- OpenIsraeliSupermarkets / `israeli-supermarket-parsers`

Boundary rules:
- The external dependency is used only to fetch raw transparency files to local disk.
- Parsing/loading those files into this project database is a separate local import step.
- Basket comparison logic must not depend on live network access.
- Tests should continue to run offline without downloader calls.

### Licensing note (third-party dependency)

The upstream OpenIsraeliSupermarkets packages referenced above are distributed under a custom non-commercial license model with attribution requirements. This project does not vendor that source code; it only integrates via external package dependency, and users should review upstream license terms before commercial use.
