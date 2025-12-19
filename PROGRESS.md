# VidSynth 项目搭建进度记录

> 对照 `MVP_framework.md` 的 Step1–Step4 目标与 `SYSTEM_DESIGN.md` 的 shared filesystem（共享文件系统）设计，汇总当前实现与待办，帮助新贡献者快速进入正确阶段。
> 开发遵循奥卡姆剃刀原理，保持代码简洁、功能独立。

## 阶段进度一览
| 阶段 | 设计目标（摘自 MVP） | 当前状态 | 产出/路径 | 下一步 |
| --- | --- | --- | --- | --- |
| Step1：片段切分 | 1fps 抽帧 + 视觉 embedding + 镜头切分 | ✅ 已完成。支持 OpenCLIP/MeanColor embedding、直方图 + 余弦阈值切分、短段合并与长段拆分 | `src/vidsynth/segment/*`、`tests/segment/*`、CLI `segment-video` | 不要删除小片段，完善日志与批处理脚本 |
| Step2：主题匹配 | clip vis_emb 与主题原型做零样本打分 | ✅ `ThemeMatcher` + `match-theme` CLI 已接入 Deepseek 原型生成，含 mean_color 回退 | `src/vidsynth/theme_match/*`、`vidsynth match-theme` | 扩展示例库、与 Step3 策略对接 |
| Step3：片段筛选/合并 | 主题分数阈值 + 连续片段聚合 | ✅ 已完成：`Sequencer` 采用上/下阈值迟滞，按相邻 clip 合并生成 EDL；提供 CLI `sequence-clips` | `src/vidsynth/sequence/*`、`vidsynth sequence-clips` | 评估不同阈值对 EDL 连贯性的影响，预留多源合并策略 |
| Step4：拼接导出 | 视觉/音频过渡 + MP4/EDL 输出 | ✅ 已完成：`Exporter` 读取 EDL，使用 `ffmpeg-python` 裁剪并拼接，音频淡入淡出；提供 CLI `export-edl` | `src/vidsynth/export/*`、`vidsynth export-edl` | 扩展多源支持与视频交叉淡入，完善导出统计与失败重试 |
| 文档与工具 | 统一配置、CLI、贡献指南 | ✅ `README.md`、`docs/CONFIG_CLI.md`、`AGENTS.md`、本文件 | `docs/*`, `AGENTS.md`, `.editorconfig` | 持续同步配置变更，补充示例数据说明 |
| Phase1：基础设施与资源层 | workspace（工作区）+ static mount（静态挂载）+ assets API（资源接口） | ✅ 已完成：创建 workspace 目录结构、更新 .gitignore，新增 FastAPI（Web 框架）server（服务端）并提供 `/api/assets` 与 `/api/import/videos`，前端 ProjectConfigModal/App 对接 API（接口） | `workspace/*`、`src/vidsynth/server/*`、`VidSynth-Visualizer/App.tsx`、`VidSynth-Visualizer/components/ProjectConfigModal.tsx` | 进入 Phase2 任务化与 SSE（服务端推送） |
| Phase2：视觉切分闭环 | 任务化 + SSE（服务端推送）+ 前端真实数据驱动 | ✅ 已完成：引入串行任务队列、任务状态落盘、SSE `/api/events` 推送近似进度；前端 Step1Segmentation 读取真实切分数据与 `/static/segmentation/{id}/clips.json` | `src/vidsynth/server/tasks.py`、`src/vidsynth/server/routers/segment.py`、`src/vidsynth/server/events.py`、`VidSynth-Visualizer/components/Step1Segmentation.tsx` | 接入 Stage2：主题匹配 API（接口）与可视化 |

## 关键产物与入口
- **配置**：`configs/baseline.yaml`（字段参见 `src/vidsynth/core/config.py` 与 CLI `--help`），可通过环境变量或 CLI 覆盖 `embedding backend`/`device` 等。
- **核心库**：`src/vidsynth/core`（数据模型、配置、日志）；`src/vidsynth/segment`（Step1 实现，含 OpenCLIP 封装）；`src/vidsynth/theme_match`（Step2）；`src/vidsynth/sequence`（Step3）；`src/vidsynth/export`（Step4）。
- **服务端**：`src/vidsynth/server`（FastAPI（Web 框架）应用、assets API（资源接口）、segment API（切分接口）、SSE（服务端推送）、static mount（静态挂载））。
- **仓库结构**：`VidSynth-Visualizer` 已并入主仓库，移除 submodule（子模块）配置，前端代码随主仓库版本追踪。
- **命令行**：
  - Step1：`vidsynth segment-video <video> -o <clips.json>`
  - Step2：`vidsynth match-theme output/clips.json "theme" -o output/theme_scores.json`
  - Step3：`vidsynth sequence-clips output/clips.json output/theme_scores.json -o output/edl.json`
  - Step4：`vidsynth export-edl output/edl.json <source_video> -o output/output_demo.mp4`
- **验证指南**：`docs/STEP1_VALIDATION.md`、`docs/STEP2_VALIDATION.md`。
- **测试**：`pytest` 覆盖 core + segment + CLI，确保每次提交前运行。
- **数据放置**：共享视频放 `workspace/videos`（前后端共用），大文件仍可存 `assets/`（或 `VIDSYNTH_STORAGE_ROOT`），测试样本放 `tests/data/`。

## 待办优先级（建议）
1. **Stage2 前后端接入**：新增 `/api/theme/expand`（Deepseek（大模型服务）后端调用）与 `/api/theme/analyze`，前端热力图（heatmap）读取 `scores.json`。
2. **Stage3/4 前后端接入**：新增 `/api/sequence/run` 与 `/api/sequence/{theme}/edl`，完成 `final_cut.mp4` 的播放与下载。
3. **多源导出扩展**：在 EDL（剪辑列表）中补齐路径字段，Exporter（导出器）支持多源合成。
4. **文档联动**：每次配置/接口变更，同时更新 `README.md`、`AGENTS.md`、`docs/CONFIG_CLI.md` 与本文件，以保持新人上手信息一致。

> 若有新增阶段或流程，请在 `My_docs/MVP_framework.md` 中先更新北极星目标，再回填此进度文件。
