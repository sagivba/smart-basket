# Retailer transparency files: local workflow and boundaries

This document describes how to use real retailer transparency files safely in local development.

## Purpose

Use retailer files to validate realistic download/import behavior without changing MVP scope:
- download raw files locally,
- import local files into SQLite,
- compare baskets from local DB data.

## Current implementation boundary

### What is implemented

- `Modules/data/remote_download.py` provides an optional integration with `il-supermarket-scraper`.
- The integration downloads raw retailer files to local folders (default `data/raw/downloads`).
- Supported chain set is constrained by current downloader configuration.

### What is explicitly out of scope

- Downloader is not the same as importer.
- Downloader does not parse files into SQLite tables.
- Downloader does not perform basket comparison.
- Download step is not required for test suite execution.

## Real local flow

1. Install dependencies from `requirements.txt`.
2. Optionally download raw retailer files to `data/raw/downloads`.
3. Import local source files into SQLite (`load products`, `load stores`, `load prices`).
4. Add basket items and run `compare`.

See `docs/run_examples.md` for safe command examples.

## Raw-data hygiene (must follow)

- Treat `data/raw/` as local-only workspace data.
- Do not commit raw retailer files.
- Use `.gitignore` defaults that keep `data/raw/.gitkeep` but ignore the rest of `data/raw/*`.
- Prefer small deterministic fixtures under `tests/fixtures/` or curated samples under `data/samples/` when adding repository-tracked data.

## External dependency role

The project currently uses `il-supermarket-scraper` only for optional download support.

Boundary expectations:
- downloader dependency is optional for development convenience,
- core import/engine/app logic remains local-first and deterministic,
- unit/integration tests must not require network connectivity,
- business logic must not leak into downloader code.

## Recommended local safeguards

- Keep raw downloads in `data/raw/downloads/` only.
- Use constrained downloads (`chains`, `file_types`, `limit`) for fast local runs.
- Remove local raw artifacts when no longer needed.
- Before commit, run `git status --short` and ensure no raw retailer files are staged.
