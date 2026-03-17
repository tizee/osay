# AGENTS.md

Instructions for AI coding agents working in this repository.

## Project Overview

- **Name**: osay
- **Type**: cli-tool
- **Python**: >=3.14
- **Package Manager**: uv

## Commands

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Run tests | `make test` or `uv run pytest tests/ -v` |
| Lint | `make lint` or `uv run ruff check src/ tests/` |
| Format | `make fmt` or `uv run ruff format src/ tests/` |
| Type check | `make typecheck` or `uv run pyright` |
| Install as tool | `make install-tool` or `uv tool install . --reinstall` |

## Code Style

- **Formatter/Linter**: ruff (configured in pyproject.toml)
- **Type checker**: pyright in strict mode
- **Docstrings**: Google style
- **Quotes**: Single quotes (enforced by ruff formatter)
- **Line length**: 100 characters
- **Layout**: src-layout (`src/osay/`)

## Rules

- Use `uv` for all package operations -- never `pip install` directly
- Run `uv run ruff check` on any new or modified files before committing
- Run `uv run pyright` on edited files -- fix errors, avoid `# type: ignore` unless necessary
- `print()` is allowed in `cli.py` and `key.py` (T20 relaxed); use `logging` elsewhere
- All package code lives under `src/osay/`
- Tests go in `tests/` using pytest
- ruff target-version is py313 (not py314) due to a ruff 0.15.x formatter bug that strips parentheses from `except (A, B):` tuples

## Architecture

- `cli.py` -- argparse CLI entry point, `main()`
- `providers.py` -- TTSProvider ABC, OpenAITTSProvider, MacOSsayProvider
- `cache.py` -- content-addressable AudioCache (SHA-256 keyed)
- `config.py` -- Config class loading `~/.config/osay/config.json`
- `key.py` -- API key management (load/save/remove from `~/.config/osay/key.json`)

## Documentation

| Document | Path | Contents |
|----------|------|----------|
| Design   | `docs/design.md` | Architecture, ASCII flowcharts, cache design, exit codes, JSON schema |
| UX       | `docs/ux.md`     | Human UX flows, agent UX (AX), feedback model, quiet mode, token efficiency |
| BDD      | `docs/bdd.md`    | Given/When/Then specifications for all features (synthesis, cache, keys, JSON, config) |
