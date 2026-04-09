# Run command examples

All commands below are verified from the repository root and use only local files.

## 1) Reset the local example database

```bash
python -c "from pathlib import Path; Path('/tmp/smart_basket_run_examples.sqlite').unlink(missing_ok=True)"
```

## 2) Load sample data into a local SQLite database

The first load command initializes the database schema at `--db-path` if the file does not exist yet.

```bash
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite load products tests/fixtures/import_products.csv --mode replace
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite load stores tests/fixtures/import_stores.csv --mode append
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite load prices tests/fixtures/import_prices.csv --mode append
```

## 3) Add basket items

```bash
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite add-item 1 12345678 --input-type barcode --quantity 2
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite add-item 1 'Bread Whole' --input-type name --quantity 1
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite add-item 1 'Unknown Snack' --input-type name --quantity 1
```

## 4) Compare a basket

```bash
python -m Modules.app.cli --db-path /tmp/smart_basket_run_examples.sqlite compare 1
```

## 5) Run the unittest suite

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```
