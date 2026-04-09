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

### 1.2 Download raw files for Shufersal only

```bash
python - <<'PY'
from pathlib import Path
import types
from unittest.mock import patch
from Modules.data.remote_download import RetailerTransparencyDownloader

class ShufersalOnlyDownloader(RetailerTransparencyDownloader):
    @staticmethod
    def _resolve_supported_chains(package_api):
        return [package_api['ScraperFactory'].SHUFERSAL]

class FakeScarpingTask:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    def start(self, limit=None, when_date=None, single_pass=True):
        _ = (limit, when_date, single_pass)
    def join(self):
        base = Path(self.kwargs['output_configuration']['base_storage_path'])
        chain = self.kwargs['enabled_scrapers'][0]
        (base / f"{chain}_PriceFull.xml").write_text('price-full', encoding='utf-8')

fake_scraper_factory = types.SimpleNamespace(SHUFERSAL='SHUFERSAL', HAZI_HINAM='HAZI_HINAM')
fake_file_types = types.SimpleNamespace(STORE_FILE='STORE_FILE', PRICE_FULL_FILE='PRICE_FULL_FILE', PRICE_FILE='PRICE_FILE')

def fake_import(name: str):
    mapping = {
        'il_supermarket_scarper': types.SimpleNamespace(ScarpingTask=FakeScarpingTask),
        'il_supermarket_scarper.scrappers_factory': types.SimpleNamespace(ScraperFactory=fake_scraper_factory),
        'il_supermarket_scarper.utils.file_types': types.SimpleNamespace(FileTypesFilters=fake_file_types),
    }
    return mapping[name]

with patch('Modules.data.remote_download.importlib.import_module', side_effect=fake_import):
    result = ShufersalOnlyDownloader().download_files(target_root='data/raw/downloads/shufersal_only_example')
    print('success=', result.success)
    print('files=', [str(f.file_path) for f in result.downloaded_files])
PY
```

### 1.3 Download raw files for Hazi Hinam only

```bash
python - <<'PY'
from pathlib import Path
import types
from unittest.mock import patch
from Modules.data.remote_download import RetailerTransparencyDownloader

class HaziHinamOnlyDownloader(RetailerTransparencyDownloader):
    @staticmethod
    def _resolve_supported_chains(package_api):
        return [package_api['ScraperFactory'].HAZI_HINAM]

class FakeScarpingTask:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    def start(self, limit=None, when_date=None, single_pass=True):
        _ = (limit, when_date, single_pass)
    def join(self):
        base = Path(self.kwargs['output_configuration']['base_storage_path'])
        chain = self.kwargs['enabled_scrapers'][0]
        (base / f"{chain}_PriceFull.xml").write_text('price-full', encoding='utf-8')

fake_scraper_factory = types.SimpleNamespace(SHUFERSAL='SHUFERSAL', HAZI_HINAM='HAZI_HINAM')
fake_file_types = types.SimpleNamespace(STORE_FILE='STORE_FILE', PRICE_FULL_FILE='PRICE_FULL_FILE', PRICE_FILE='PRICE_FILE')

def fake_import(name: str):
    mapping = {
        'il_supermarket_scarper': types.SimpleNamespace(ScarpingTask=FakeScarpingTask),
        'il_supermarket_scarper.scrappers_factory': types.SimpleNamespace(ScraperFactory=fake_scraper_factory),
        'il_supermarket_scarper.utils.file_types': types.SimpleNamespace(FileTypesFilters=fake_file_types),
    }
    return mapping[name]

with patch('Modules.data.remote_download.importlib.import_module', side_effect=fake_import):
    result = HaziHinamOnlyDownloader().download_files(target_root='data/raw/downloads/hazi_hinam_only_example')
    print('success=', result.success)
    print('files=', [str(f.file_path) for f in result.downloaded_files])
PY
```

### 1.4 Download raw files for both chains together

```bash
python - <<'PY'
from pathlib import Path
import types
from unittest.mock import patch
from Modules.data.remote_download import RetailerTransparencyDownloader

class FakeScarpingTask:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    def start(self, limit=None, when_date=None, single_pass=True):
        _ = (limit, when_date, single_pass)
    def join(self):
        base = Path(self.kwargs['output_configuration']['base_storage_path'])
        chain = self.kwargs['enabled_scrapers'][0]
        (base / f"{chain}_PriceFull.xml").write_text('price-full', encoding='utf-8')

fake_scraper_factory = types.SimpleNamespace(SHUFERSAL='SHUFERSAL', HAZI_HINAM='HAZI_HINAM')
fake_file_types = types.SimpleNamespace(STORE_FILE='STORE_FILE', PRICE_FULL_FILE='PRICE_FULL_FILE', PRICE_FILE='PRICE_FILE')

def fake_import(name: str):
    mapping = {
        'il_supermarket_scarper': types.SimpleNamespace(ScarpingTask=FakeScarpingTask),
        'il_supermarket_scarper.scrappers_factory': types.SimpleNamespace(ScraperFactory=fake_scraper_factory),
        'il_supermarket_scarper.utils.file_types': types.SimpleNamespace(FileTypesFilters=fake_file_types),
    }
    return mapping[name]

with patch('Modules.data.remote_download.importlib.import_module', side_effect=fake_import):
    result = RetailerTransparencyDownloader().download_files(target_root='data/raw/downloads/both_chains_example')
    print('success=', result.success)
    print('chains=', result.requested_chains)
    print('files=', [str(f.file_path) for f in result.downloaded_files])
PY
```

### 1.5 Prefer full price files with fallback to regular price files

```bash
python - <<'PY'
from pathlib import Path
import types
from unittest.mock import patch
from Modules.data.remote_download import RetailerTransparencyDownloader

class FakeScarpingTask:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    def start(self, limit=None, when_date=None, single_pass=True):
        _ = (limit, when_date, single_pass)
    def join(self):
        base = Path(self.kwargs['output_configuration']['base_storage_path'])
        chain = self.kwargs['enabled_scrapers'][0]
        (base / f"{chain}_Price.xml").write_text('price', encoding='utf-8')

fake_scraper_factory = types.SimpleNamespace(SHUFERSAL='SHUFERSAL', HAZI_HINAM='HAZI_HINAM')
fake_file_types = types.SimpleNamespace(STORE_FILE='STORE_FILE', PRICE_FULL_FILE='PRICE_FULL_FILE', PRICE_FILE='PRICE_FILE')

def fake_import(name: str):
    mapping = {
        'il_supermarket_scarper': types.SimpleNamespace(ScarpingTask=FakeScarpingTask),
        'il_supermarket_scarper.scrappers_factory': types.SimpleNamespace(ScraperFactory=fake_scraper_factory),
        'il_supermarket_scarper.utils.file_types': types.SimpleNamespace(FileTypesFilters=fake_file_types),
    }
    return mapping[name]

with patch('Modules.data.remote_download.importlib.import_module', side_effect=fake_import):
    import shutil
    shutil.rmtree('data/raw/downloads/prefer_full_fallback_example', ignore_errors=True)
    result = RetailerTransparencyDownloader().download_files(
        target_root='data/raw/downloads/prefer_full_fallback_example',
        prefer_full_price_files=True,
    )
    print('success=', result.success)
    print('warnings=', result.warnings)
PY
```

### 1.6 Include store files

```bash
python - <<'PY'
from pathlib import Path
import types
from unittest.mock import patch
from Modules.data.remote_download import RetailerTransparencyDownloader

class FakeScarpingTask:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    def start(self, limit=None, when_date=None, single_pass=True):
        _ = (limit, when_date, single_pass)
    def join(self):
        base = Path(self.kwargs['output_configuration']['base_storage_path'])
        chain = self.kwargs['enabled_scrapers'][0]
        (base / f"{chain}_Store.xml").write_text('store', encoding='utf-8')
        (base / f"{chain}_Price.xml").write_text('price', encoding='utf-8')

fake_scraper_factory = types.SimpleNamespace(SHUFERSAL='SHUFERSAL', HAZI_HINAM='HAZI_HINAM')
fake_file_types = types.SimpleNamespace(STORE_FILE='STORE_FILE', PRICE_FULL_FILE='PRICE_FULL_FILE', PRICE_FILE='PRICE_FILE')

def fake_import(name: str):
    mapping = {
        'il_supermarket_scarper': types.SimpleNamespace(ScarpingTask=FakeScarpingTask),
        'il_supermarket_scarper.scrappers_factory': types.SimpleNamespace(ScraperFactory=fake_scraper_factory),
        'il_supermarket_scarper.utils.file_types': types.SimpleNamespace(FileTypesFilters=fake_file_types),
    }
    return mapping[name]

with patch('Modules.data.remote_download.importlib.import_module', side_effect=fake_import):
    import shutil
    shutil.rmtree('data/raw/downloads/include_store_files_example', ignore_errors=True)
    result = RetailerTransparencyDownloader().download_files(
        target_root='data/raw/downloads/include_store_files_example',
        include_store_files=True,
        prefer_full_price_files=False,
    )
    print('success=', result.success)
    print('types=', sorted({f.file_type for f in result.downloaded_files}))
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
