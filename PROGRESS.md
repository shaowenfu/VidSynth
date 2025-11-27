# VidSynth 项目搭建进度记录

> 对照 `develop_docs/MVP_framework.md` 的 Step1–Step4 目标，汇总当前实现与待办，帮助新贡献者快速进入正确阶段。
> 开发遵循奥卡姆剃刀原理，保持代码简洁、功能独立。

## 阶段进度一览
| 阶段 | 设计目标（摘自 MVP） | 当前状态 | 产出/路径 | 下一步 |
| --- | --- | --- | --- | --- |
| Step1：片段切分 | 1fps 抽帧 + 视觉 embedding + 镜头切分 | ✅ 已完成。支持 OpenCLIP/MeanColor embedding、直方图 + 余弦阈值切分、短段合并与长段拆分 | `src/vidsynth/segment/*`、`tests/segment/*`、CLI `segment-video` | 不要删除小片段，完善日志与批处理脚本 |
| Step2：主题匹配 | clip vis_emb 与主题原型做零样本打分 | ✅ `ThemeMatcher` + `match-theme` CLI 已接入 Deepseek 原型生成，含 mean_color 回退 | `src/vidsynth/theme_match/*`、`vidsynth match-theme` | 扩展示例库、与 Step3 策略对接 |
| Step3：片段筛选/合并 | 主题分数阈值 + 连续片段聚合 | ✅ 已完成：`Sequencer` 采用上/下阈值迟滞，按相邻 clip 合并生成 EDL；提供 CLI `sequence-clips` | `src/vidsynth/sequence/*`、`vidsynth sequence-clips` | 评估不同阈值对 EDL 连贯性的影响，预留多源合并策略 |
| Step4：拼接导出 | 视觉/音频过渡 + MP4/EDL 输出 | ✅ 已完成：`Exporter` 读取 EDL，使用 `ffmpeg-python` 裁剪并拼接，音频淡入淡出；提供 CLI `export-edl` | `src/vidsynth/export/*`、`vidsynth export-edl` | 扩展多源支持与视频交叉淡入，完善导出统计与失败重试 |
| 文档与工具 | 统一配置、CLI、贡献指南 | ✅ `README.md`、`docs/CONFIG_CLI.md`、`AGENTS.md`、本文件 | `docs/*`, `AGENTS.md`, `.editorconfig` | 持续同步配置变更，补充示例数据说明 |

## 关键产物与入口
- **配置**：`configs/baseline.yaml`（字段参见 `src/vidsynth/core/config.py` 与 CLI `--help`），可通过环境变量或 CLI 覆盖 `embedding backend`/`device` 等。
- **核心库**：`src/vidsynth/core`（数据模型、配置、日志）；`src/vidsynth/segment`（Step1 实现，含 OpenCLIP 封装）；`src/vidsynth/theme_match`（Step2）；`src/vidsynth/sequence`（Step3）；`src/vidsynth/export`（Step4）。
- **命令行**：
  - Step1：`vidsynth segment-video <video> -o <clips.json>`
  - Step2：`vidsynth match-theme output/clips.json "theme" -o output/theme_scores.json`
  - Step3：`vidsynth sequence-clips output/clips.json output/theme_scores.json -o output/edl.json`
  - Step4：`vidsynth export-edl output/edl.json <source_video> -o output/output_demo.mp4`
- **验证指南**：`docs/STEP1_VALIDATION.md`、`docs/STEP2_VALIDATION.md`。
- **测试**：`pytest` 覆盖 core + segment + CLI，确保每次提交前运行。
- **数据放置**：大文件存 `assets/`（或 `VIDSYNTH_STORAGE_ROOT`），测试样本放 `tests/data/`。

## 待办优先级（建议）
1. **Step3 策略**：在 `theme_score` 基础上设计筛选/聚合算法及 CLI 接口。
2. **标签/描述扩展**：基于 `LabelBackend` 接口，为 Clip 生成描述，方便后续筛选与 UI。
3. **批处理脚本**：在 `scripts/` 中加入批量 `segment-video` 或评估脚本，记录运行日志。
4. **导出阶段设计**: 制定 `sequencer`/`export` API，明确输入 JSON 契约，避免后期返工。
5. **文档联动**：每次配置/接口变更，同时更新 `README.md`、`AGENTS.md`、`docs/CONFIG_CLI.md` 与本文件，以保持新人上手信息一致。

> 若有新增阶段或流程，请在 `My_docs/MVP_framework.md` 中先更新北极星目标，再回填此进度文件。*** End Patch
