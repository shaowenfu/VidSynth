# VidSynth

主题驱动的多源视频自动编排 MVP，聚焦验证“关键帧抽样 → 视觉 embedding → 主题匹配 → 片段编排”的可行性。项目遵循奥卡姆剃刀原则：先用最小可跑 pipeline 验证逻辑，再逐步替换更高质量模型。

## 数据准备
- **原始视频**：放在 `assets/` 或通过环境变量 `VIDSYNTH_STORAGE_ROOT` 指向的大容量磁盘。保持目录结构简单，例如 `assets/raw/{project}/{video.mp4}`。
- **测试样例**：体积小、可公开的 mp4 放在 `tests/data/`，用于单元测试；不要把大文件提交到 Git。
- **视频清单**：可在 `scripts/` 下维护 CSV/JSON，记录 `video_id`、路径、拍摄主题等，供批处理脚本使用。

## 安装与配置
```bash
python -m venv venv && source venv/bin/activate
pip install -e .[dev]
pre-commit install
```

- 默认配置位于 `configs/baseline.yaml`，字段说明详见 `docs/CONFIG_CLI.md`。
- 若使用 OpenCLIP，请确保已安装 `open-clip-torch`、`pillow`，并根据机器资源设置：
  - CPU: `embedding.backend=open_clip`, `preset=cpu-small`, `device=cpu`
  - GPU: `preset=gpu-large`, `device=cuda` 或 `cuda:0`
- 全局环境变量示例：
  ```bash
  export VIDSYNTH_STORAGE_ROOT=/data/vidsynth-assets
  export VIDSYNTH_EMBEDDING_BACKEND=open_clip
  export VIDSYNTH_EMBEDDING_DEVICE=cuda
  ```
- 本地开发默认加载根目录 `.env`（由配置模块自动解析），可在其中填入 `DEEPSEEK_API_KEY` 等敏感配置而无需暴露到 shell。

## 使用流程
1. **Step1: 片段切分**
   ```bash
   vidsynth segment-video assets/raw/beach.mp4 \
     --output out/beach_clips.json \
     --config configs/baseline.yaml
   ```
   - 输入：单个视频路径 + 配置。
   - 输出：`out/beach_clips.json`，包含 `Clip` 对象数组（`video_id`、`t_start/t_end`、`vis_emb_avg`、`emb_model` 等）。
   - 日志：打印镜头切分统计、丢弃片段数量。
2. **Step2: 主题匹配**
   ```bash
   vidsynth match-theme output/beach_clips.json "beach vacation" \\
     --output output/beach_scores.json \\
     --embedding-backend open_clip --embedding-device cpu
   ```
   - 输入：Step1 导出的 Clip JSON + 主题关键词（可附加 `--positive/--negative` 描述）。
   - 输出：`theme_score` JSON/CSV，包含 `score/s_pos/s_neg` 等字段，可依 `--score-threshold` 筛选。
   - 说明：若 Clip 使用 `mean_color` 占位 embedding，会安全回退为 0 分，需改用 OpenCLIP 重新切分以获取有效结果。
3. **Step3: 片段筛选/合并（部分在 Step1 中实现）**：当前 `segment_video` 已处理短片段合并与长片段拆分；未来可在此基础上叠加主题阈值筛选。
4. **Step4: 拼接导出（计划中）**：读取经过筛选的 Clip 列表，通过 `ffmpeg` 导出 MP4 与 JSON EDL。

## 目录结构速览
- `src/vidsynth/core`: 数据模型、配置、日志、路径工具。
- `src/vidsynth/segment`: Step2 实现（采样、embedding、镜头切分、标签接口）。
- `configs/`: baseline 及自定义 YAML。
- `scripts/`: 批处理/实验脚本。
- `tests/`: 单元与集成测试，结构与 `src` 镜像。
- `docs/CONFIG_CLI.md`: 配置字段与 CLI 命令详解。
- `docs/PROGRESS.md`: 针对 `develop_docs/MVP_framework.md` 的阶段进度记录。
- `docs/STEP1_VALIDATION.md` / `docs/STEP2_VALIDATION.md`: 各阶段的验证手册。
- `AGENTS.md`: 贡献者指南。

## 输出产物
- `*.json` Clip 清单：每个 clip 包含时间段、embedding 均值、使用的模型等，可直接供主题匹配或序列化存储。
- 未来步骤（待完成）：主题得分文件、拼接后 MP4、EDL 列表。

## 贡献指南
- 请遵循 `AGENTS.md`、`docs/CONFIG_CLI.md` 与 `docs/PROGRESS.md` 指引，确保实现与文档一致。
- 提交前运行 `pytest` + `ruff check` + `black` 并确保 CLI 示例可以执行。
