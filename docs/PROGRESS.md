# VidSynth 项目搭建进度记录

> 对照 `develop_docs/MVP_framework.md` 的 Step1–Step4 目标，汇总当前实现与待办，帮助新贡献者快速进入正确阶段。
> 开发遵循奥卡姆剃刀原理，保持代码简洁、功能独立。

## 阶段进度一览
| 阶段 | 设计目标（摘自 MVP） | 当前状态 | 产出/路径 | 下一步 |
| --- | --- | --- | --- | --- |
| Step1：片段切分 | 1fps 抽帧 + 视觉 embedding + 镜头切分 | ✅ 已完成。支持 OpenCLIP/MeanColor embedding、直方图 + 余弦阈值切分、短段合并与长段拆分 | `src/vidsynth/segment/*`、`tests/segment/*`、CLI `segment-video` | 提升 embedding 后端为真实 CLIP（默认预设已就绪），完善日志与批处理脚本 |
| Step2：主题匹配 | clip vis_emb 与主题原型做零样本打分 | ⏳ 未实现。当前仅提供 `ThemeQuery` 数据模型 | 参考 `src/vidsynth/core/datamodels.py` | 实现 `theme_match` 模块：主题原型生成、正/负样本相似度、得分输出 JSON/CSV |
| Step3：片段筛选/合并 | 主题分数阈值 + 连续片段聚合 | ⚙️ 部分实现：`SegmentConfig` 已支持 `merge_short_segments`/`split_long_segments`，但尚未结合主题分数 | `src/vidsynth/segment/clipper.py` | 在 Step2 输出的 `theme_score` 基础上，加入筛选器与策略参数 |
| Step4：拼接导出 | 视觉/音频过渡 + MP4/EDL 输出 | ⛔ 未开始 | 仅在 `configs/baseline.yaml` 留有导出参数占位 | 设计 `sequencer` + `export` 模块：读取 Clip + EDL，调用 ffmpeg 生成最终视频 |
| 文档与工具 | 统一配置、CLI、贡献指南 | ✅ `README.md`、`docs/CONFIG_CLI.md`、`AGENTS.md`、本文件 | `docs/*`, `AGENTS.md`, `.editorconfig` | 持续同步配置变更，补充示例数据说明 |

## 关键产物与入口
- **配置**：`configs/baseline.yaml`（详解见 `docs/CONFIG_CLI.md`），可通过环境变量或 CLI 覆盖 `embedding backend`/`device` 等。
- **核心库**：`src/vidsynth/core`（数据模型、配置、日志）；`src/vidsynth/segment`（Step1 实现，含 OpenCLIP 封装）。
- **命令行**：`python -m vidsynth.cli segment-video <video> -o <clips.json>`；支持 `--embedding-backend` / `--embedding-preset` / `--embedding-device`。
- **测试**：`pytest` 覆盖 core + segment + CLI，确保每次提交前运行。
- **数据放置**：大文件存 `assets/`（或 `VIDSYNTH_STORAGE_ROOT`），测试样本放 `tests/data/`。

## 待办优先级（建议）
1. **主题匹配模块**：实现 Step2 逻辑，输出 `theme_score` 并与 Step1 流水打通。
2. **标签/描述扩展**：基于 `LabelBackend` 接口，为 Clip 生成描述，方便后续筛选与 UI。
3. **批处理脚本**：在 `scripts/` 中加入批量 `segment-video` 或评估脚本，记录运行日志。
4. **导出阶段设计**: 制定 `sequencer`/`export` API，明确输入 JSON 契约，避免后期返工。
5. **文档联动**：每次配置/接口变更，同时更新 `README.md`、`AGENTS.md`、`docs/CONFIG_CLI.md` 与本文件，以保持新人上手信息一致。

> 若有新增阶段或流程，请在 `develop_docs/MVP_framework.md` 中先更新北极星目标，再回填此进度文件。*** End Patch
