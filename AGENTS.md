# Repository Guidelines

## Project Structure & Module Organization
`develop_docs/` stores architecture notes; revise `develop_docs/MVP_framework.md` whenever the Step1–Step4 pipeline changes. Implementation belongs in `src/vidsynth/` (create the tree if missing) with focused subpackages such as `ingest`, `segment`, `theme_match`, `sequencer`, and `export`, plus shared helpers in `src/vidsynth/core`. Mirror this layout in `tests/`, keep deterministic clips in `tests/data/`, and place bulky footage inside `assets/` or external buckets referenced via config. Treat `configs/` as the source of truth for YAML presets, while the root-level `venv/` stays developer-local and untracked elsewhere.

## Build, Test, and Development Commands
Use Python 3.10+: `python -m venv venv && source venv/bin/activate`. Install everything via `pip install -e .[dev]` (pyproject 管理依赖)，然后执行 `pre-commit install` 保证本地钩子生效。运行端到端切分流程时使用 `python -m vidsynth.cli segment-video assets/raw/demo.mp4 -o out/demo_clips.json --config configs/baseline.yaml`，或在安装脚本后使用 `vidsynth segment-video ...`。提交前至少跑 `pytest`, `ruff check src tests`, `black src tests`；如修改 CLI/config，附带一个实际命令示例并记录在 `docs/CONFIG_CLI.md`。

## Coding Style & Naming Conventions
Follow PEP8, four-space indentation, exhaustive type hints, and dataclasses for clip metadata. Modules and functions use `snake_case`, classes use `CapWords`, and constants use `UPPER_SNAKE`. Keep functions short, avoid hidden state, and document public APIs with a one-sentence docstring noting the MVP step they implement so future agents can trace responsibilities quickly.

## Testing Guidelines
Pytest drives validation and mirrors the `src` layout. Prefer fixtures to build clip dictionaries and keep reproducible mp4 snippets in `tests/data/`. Tag GPU-heavy suites with `@pytest.mark.slow`, and pair every new feature with at least one regression test plus a schema assertion for emitted EDL/JSON artifacts.

## Commit & Pull Request Guidelines
Stick to Conventional Commits (`type: summary`) as illustrated by `docs: 添加主题驱动多源视频自动编排系统框架文档`, keeping each commit scoped to one concern. PRs must contain a problem statement, approach summary, sample command/output (EDL snippet or screenshot), and a checklist of tests/documentation updates. Always link related issues and tag stage owners (e.g., sequencing maintainers for Step4 changes) to keep review cycles short.

## Documentation & Configuration Tips
更新文档遵循“源文件+指南”双轨：`develop_docs/MVP_framework.md` 保持原始设计目标；`docs/CONFIG_CLI.md` 记录具体参数和 CLI 用法；`docs/PROGRESS.md` 展示阶段进度。调整阈值、路径或新模块时同步更新这些文件。敏感配置写 `.env`（参考 `.env.example`），永远不要把真实密钥写入仓库。*** End Patch
