# Repository Guidelines

## Project Structure & Module Organization
`develop_docs/` stores architecture notes; revise `develop_docs/MVP_framework.md` whenever the Step1–Step4 pipeline changes. Implementation belongs in `src/vidsynth/` (create the tree if missing) with focused subpackages such as `ingest`, `segment`, `theme_match`, `sequencer`, and `export`, plus shared helpers in `src/vidsynth/core`. Mirror this layout in `tests/`, keep deterministic clips in `tests/data/`, and place bulky footage inside `assets/` or external buckets referenced via config. Treat `configs/` as the source of truth for YAML presets, while the root-level `venv/` stays developer-local and untracked elsewhere.

## Build, Test, and Development Commands
Use Python 3.10+: `python -m venv venv && source venv/bin/activate`. Install runtime deps with `pip install -r requirements.txt` and dev tooling via `pip install -r requirements-dev.txt`. Exercise the full flow through `python -m vidsynth.cli --theme "beach" --videos data/beach/*.mp4 --out out/beach.mp4`, keeping automation wrappers in `scripts/`. Run `python -m pytest tests` before committing, and finish every session with `ruff check src tests && black src tests` to keep style drift out of PRs.

## Coding Style & Naming Conventions
Follow PEP8, four-space indentation, exhaustive type hints, and dataclasses for clip metadata. Modules and functions use `snake_case`, classes use `CapWords`, and constants use `UPPER_SNAKE`. Keep functions short, avoid hidden state, and document public APIs with a one-sentence docstring noting the MVP step they implement so future agents can trace responsibilities quickly.

## Testing Guidelines
Pytest drives validation and mirrors the `src` layout. Prefer fixtures to build clip dictionaries and keep reproducible mp4 snippets in `tests/data/`. Tag GPU-heavy suites with `@pytest.mark.slow`, and pair every new feature with at least one regression test plus a schema assertion for emitted EDL/JSON artifacts.

## Commit & Pull Request Guidelines
Stick to Conventional Commits (`type: summary`) as illustrated by `docs: 添加主题驱动多源视频自动编排系统框架文档`, keeping each commit scoped to one concern. PRs must contain a problem statement, approach summary, sample command/output (EDL snippet or screenshot), and a checklist of tests/documentation updates. Always link related issues and tag stage owners (e.g., sequencing maintainers for Step4 changes) to keep review cycles short.

## Documentation & Configuration Tips
Update `develop_docs/MVP_framework.md` and the relevant `configs/*.yaml` whenever thresholds, embeddings, or export settings move. Record required environment variables inside `docs/secrets.md`, store actual keys in ignored `.env` files, and provide default config values so automation agents can run unattended locally or in CI.
