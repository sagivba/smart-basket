# Run command examples

Examples below were re-run from the repository root. Downloader examples are **Python API snippets** (the downloader is not exposed as a CLI command in this repository).

The first step can now download raw transparency files for:
- `SHUFERSAL`
- `HAZI_HINAM`

## 1) Download raw transparency files (Python API)

### 1.1 Clean the download target folder

```bash
python -c "from pathlib import Path; import shutil; shutil.rmtree('data/raw/downloads', ignore_errors=True); Path('data/raw/downloads').mkdir(parents=True, exist_ok=True)"
```

### 1.2 Download all supported chains and print a report

```bash
python - <<'PY'
from Modules.data.remote_download import RetailChainsDownloadManager

manager = RetailChainsDownloadManager()
result = manager.download_chains(target_root='data/raw/downloads')
print('success=', result.success)
print(manager.render_report(result))
PY
```

> `render_report(...)` is safe to call for both successful and failed runs and always returns text output.
Real runs may create nested folders such as:
- `data/raw/downloads/shufersal/Shufersal/`
- `data/raw/downloads/hazi_hinam/HaziHinam/`

### 1.3 Download raw files for Shufersal only

```bash
python - <<'PY'
from Modules.data.remote_download import RetailChainsDownloadManager

manager = RetailChainsDownloadManager()
result = manager.download_chains(
    target_root='data/raw/downloads',
    chains=['SHUFERSAL'],
)
print('success=', result.success)
print(manager.render_report(result))
PY
```

### 1.4 Download raw files for Hazi Hinam only

```bash
python - <<'PY'
from Modules.data.remote_download import RetailChainsDownloadManager

manager = RetailChainsDownloadManager()
result = manager.download_chains(
    target_root='data/raw/downloads',
    chains=['HAZI_HINAM'],
)
print('success=', result.success)
print(manager.render_report(result))
PY
```

### 1.5 Download only selected file types

```bash
python - <<'PY'
from Modules.data.remote_download import RetailChainsDownloadManager

manager = RetailChainsDownloadManager()
result = manager.download_chains(
    target_root='data/raw/downloads',
    file_types=['STORE_FILE', 'PRICE_FULL_FILE'],
)
print('success=', result.success)
print(manager.render_report(result))
PY
```

### 1.6 Constrained download (safer default for regular runs)

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

### 1.7 Cleanup target chain folder before download

```bash
python - <<'PY'
from Modules.data.remote_download import RetailChainsDownloadManager

manager = RetailChainsDownloadManager()
result = manager.download_chains(
    target_root='data/raw/downloads',
    chains=['HAZI_HINAM'],
    file_types=['STORE_FILE'],
    cleanup_before_download=True,
)
print('success=', result.success)
print(manager.render_report(result))
PY
```

### 1.8 Download and print report only (quick diagnostic)

```bash
python - <<'PY'
from Modules.data.remote_download import RetailChainsDownloadManager

manager = RetailChainsDownloadManager()
result = manager.download_chains(
    target_root='data/raw/downloads',
    chains=['SHUFERSAL', 'HAZI_HINAM'],
    limit=5,
)
print(manager.render_report(result))
PY
```

> Note: this step downloads raw retailer files only. Parsing/loading XML/GZ files into SQLite is a separate step.

## 2) Reset the local example database

```bash
python -c "from pathlib import Path; Path('/tmp/smart_basket_run_examples.sqlite').unlink(missing_ok=True)"
```

## 3) Load sample data into a local SQLite database

The first load command initializes the database schema at `--db-path` if the file does not exist yet.

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

## 5) Compare a basket

```bash
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite compare 1
```

## 6) Run downloader unit tests only

```bash
python -m unittest tests.unit.test_remote_download -v
```

## 7) Run the full unittest suite

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```
