# Run command examples

Examples below are safe for local use and do **not** require committing raw retailer data.

## Safety rules before you run examples

- Keep raw retailer downloads under `data/raw/downloads/` only.
- Do not stage files under `data/raw/` for commit.
- Use `/tmp` for ad-hoc SQLite files.
- Prefer deterministic fixtures for import and tests.

See `docs/retailer_files.md` for workflow and dependency boundaries.

## 1) Optional: download raw transparency files (Python API)

The downloader is available as a Python API (not a dedicated CLI command).
This step is optional for local dev and not required for tests.

### 1.1 Reset local download target

```bash
python -c "from pathlib import Path; import shutil; shutil.rmtree('data/raw/downloads', ignore_errors=True); Path('data/raw/downloads').mkdir(parents=True, exist_ok=True)"
```

### 1.2 Constrained download (recommended default)

```bash
python - <<'PY'
from datetime import date
from Modules.data.remote_download import RetailChainsDownloadManager

manager = RetailChainsDownloadManager()
result = manager.download_chains(
    target_root='data/raw/downloads',
    chains=['SHUFERSAL'],
    file_types=['STORE_FILE', 'PRICE_FILE'],
    when_date=date(2026, 1, 15),
    limit=25,
)
print('success=', result.success)
print(manager.render_report(result))
PY
```

> Note: this downloads raw files only. Importing into SQLite is a separate step.

## 2) Reset the local example database

```bash
python -c "from pathlib import Path; Path('/tmp/smart_basket_run_examples.sqlite').unlink(missing_ok=True)"
```

## 3) Load deterministic fixture data into local SQLite

The first load command initializes schema at `--db-path` if needed.

```bash
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite load products tests/fixtures/import_products.csv --mode replace
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite load stores tests/fixtures/import_stores.csv --mode replace
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite load prices tests/fixtures/import_prices.csv --mode append
```

## 4) Add basket items

```bash
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite add-item 1 12345678 --input-type barcode --quantity 2
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite add-item 1 'Bread Whole' --input-type name --quantity 1
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite add-item 1 'Unknown Snack' --input-type name --quantity 1
```

## 5) Compare basket

```bash
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite compare 1
```

## 6) Check raw-data hygiene before commit

```bash
git status --short
```

## 7) Run downloader unit tests only

```bash
python -m unittest tests.unit.test_remote_download -v
```

## 8) Run the full unittest suite

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```
