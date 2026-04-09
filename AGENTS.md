# AGENTS.md

## Project overview

This repository implements a local-first basket comparison engine for retail price data.

Primary goals:
- load local product and price files
- normalize and store data in local SQLite
- accept basket input by barcode or product name
- compare basket cost across retail chains
- report missing items and unmatched inputs
- return ranked results with line-level pricing details

Current stage:
- MVP only
- no backend
- no remote sync
- no web UI
- no user management

Target stack:
- Python 3.12
- SQLite
- unittest
- minimal external dependencies

## Repository structure

- `README.md` - project entry point
- `AGENTS.md` - instructions for coding agents
- `requirements.txt` - minimal Python dependencies
- `.env.example` - local configuration example if needed
- `TODO.md` - pending work and follow-up items
- `docs/system_spec.md` - system specification
- `docs/module_guide.md` - module-level guidance
- `docs/test_strategy.md` - testing guidance
- `Modules/app/` - application orchestration and use cases
- `Modules/data/` - parsing and loading of local source files
- `Modules/db/` - SQLite schema, repositories, persistence
- `Modules/engine/` - basket matching, calculation, comparison, ranking
- `Modules/models/` - entities, DTOs, result models, shared enums/constants
- `Modules/utils/` - shared utility helpers only
- `tests/fixtures/` - deterministic local fixtures
- `tests/unit/` - unit tests
- `data/raw/` - source input files
- `data/samples/` - sample files for development and tests
- `data/generated/` - generated outputs if needed

## Architectural boundaries

Keep the layered design strict.

### Modules/data
Responsible for:
- reading supported local file formats
- field normalization
- parse-level validation
- controlled loading of parsed records into the db layer
- import summaries and error reporting

Must not:
- implement basket comparison rules
- contain chain ranking logic
- become a general orchestration layer

### Modules/db
Responsible for:
- SQLite connections
- schema creation and maintenance for the current MVP
- repositories and query logic
- persistence operations and read models

Must not:
- make business decisions
- parse files
- orchestrate end-to-end application flows

### Modules/engine
Responsible for:
- matching basket inputs to products
- fetching price data through db-facing abstractions
- detecting missing items
- computing totals
- ranking chains
- producing structured comparison results

Must not:
- read raw files directly
- own file parsing logic
- take over CLI or UI responsibilities

### Modules/app
Responsible for:
- use case orchestration
- coordinating data, db, and engine modules
- returning stable outputs for future CLI or other consumers

Must stay thin:
- no heavy business logic
- no raw parsing logic
- no uncontrolled SQL logic when repository methods are available

### Modules/models
Responsible for:
- domain entities
- result objects
- simple shared enums/constants
- contracts passed between layers

Must not:
- own infrastructure logic
- own parsing or persistence workflows
- accumulate unrelated helper logic

### Modules/utils
Responsible for:
- focused shared helpers such as text normalization and validation

Must not:
- absorb business rules that belong in engine
- absorb persistence logic that belongs in db
- become a dumping ground for unrelated code

## Default MVP behavior

Unless a task explicitly changes business rules, preserve these defaults:

- comparison scope is chain-level, not branch selection by user
- representative chain price is the minimum available price across that chain's stores
- ranking is two-stage:
  1. complete baskets first
  2. partial baskets second
  3. within each group, lower total price first
- unmatched basket inputs are excluded from total price calculation
- unmatched basket inputs must be returned separately
- missing products in a chain must be reported clearly
- quantity must be a positive integer for MVP
- product-name matching starts with simple normalization and string matching only
- do not introduce advanced NLP-based matching unless explicitly requested
- keep the project fully local-first and offline-capable

## Coding rules

- keep changes small and local
- prefer minimal diffs
- do not perform broad refactors unless explicitly requested
- do not rename public interfaces casually
- do not move code across layers without a clear architectural reason
- do not mix I/O, business logic, and persistence in the same component
- prefer small functions with one clear responsibility
- prefer cohesive classes when they improve clarity
- use clear names and explicit types where helpful
- keep code deterministic and runnable offline

## Dependency policy

- prefer Python standard library first
- every new dependency must be justified
- update `requirements.txt` for every added dependency
- document non-obvious dependency decisions in `README.md` or `docs/`
- avoid heavy frameworks in MVP

## Testing policy

Use `unittest` only.

Do not use:
- pytest
- network-dependent tests
- flaky time-dependent tests

Required rules:
- every code change must include relevant tests
- every bug fix must include a regression test
- every new capability must include at least one unit test
- add broader tests only when the change crosses module boundaries
- tests must be deterministic and local

Test layout:
- `tests/unit/`
- `tests/fixtures/`

Run tests from repository root:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## Documentation rules

Update documentation when behavior or structure changes.

Required documentation updates for:
- public behavior changes
- schema changes
- new entry points
- new dependencies
- changed comparison rules
- changed file format assumptions

Docstrings:
- public classes should have short docstrings
- comments should explain why, not obvious what

## Change control for agents

Before editing:
1. identify the target module
2. verify the task belongs in that module
3. check whether tests already cover the behavior
4. prefer the smallest valid implementation

While editing:
- touch only files directly related to the task
- avoid opportunistic cleanup
- do not modify docs or schema unless required

After editing:
- run relevant tests
- verify imports and module boundaries
- summarize exactly what changed and why

## Out of scope for current MVP

Do not add these unless explicitly requested:
- backend services
- REST API
- web UI
- authentication or authorization
- cloud dependencies
- remote synchronization
- advanced promotions engine
- coupon logic
- recommendation engine
- full NLP search stack
- third-party checkout or POS integrations

## If requirements are ambiguous

Choose the simplest implementation that:
- preserves the current layered architecture
- keeps MVP scope intact
- minimizes dependencies
- remains fully testable offline
