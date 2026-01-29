# VidSynth

主题驱动的多源视频自动编排 MVP，聚焦验证“关键帧抽样 → 视觉 embedding → 主题匹配 → 片段编排”的可行性。项目遵循奥卡姆剃刀原则：先用最小可跑 pipeline 验证逻辑，再逐步替换更高质量模型。

## 数据准备
- **原始视频**：放在 `assets/` 或通过环境变量 `VIDSYNTH_STORAGE_ROOT` 指向的大容量磁盘。保持目录结构简单，例如 `assets/raw/{project}/{video.mp4}`。
- **测试样例**：体积小、可公开的 mp4 放在 `tests/data/`，用于单元测试；不要把大文件提交到 Git。
- **视频清单**：可在 `scripts/` 下维护 CSV/JSON（数据格式），记录 `video_id`、路径、拍摄主题等，供批处理脚本使用。

## 安装与配置
```bash
python -m venv venv && source venv/bin/activate
pip install -e .[dev]
pre-commit install
```

- 默认配置位于 `configs/baseline.yaml`（YAML 配置）；字段说明参考源码 `src/vidsynth/core/config.py`。
- 若使用 OpenCLIP（视觉模型），请确保已安装 `open-clip-torch`、`pillow`，并根据机器资源设置：
  - CPU（处理器）: `embedding.backend=open_clip`, `preset=cpu-small`, `device=cpu`
  - GPU（显卡）: `preset=gpu-large`, `device=cuda` 或 `cuda:0`
- 全局环境变量示例：
  ```bash
  export VIDSYNTH_STORAGE_ROOT=/data/vidsynth-assets
  export VIDSYNTH_EMBEDDING_BACKEND=open_clip
  export VIDSYNTH_EMBEDDING_DEVICE=cuda
  ```
- 本地开发默认加载根目录 `.env`（由配置模块自动解析），可在其中填入 `DEEPSEEK_API_KEY` 等敏感配置而无需暴露到 shell。

## 使用流程
1. **启动后端服务**：使用 FastAPI（后端框架）启动 `vidsynth.server.app:app`，在 `/docs` 查看 API（接口）说明。
2. **前端协作**：前端通过 `/api/*` 调度 Step1-4，并通过 `/static/*` 读取产物。
3. **可变参数**：通过 `/api/settings` 更新配置；服务端会写入 `workspace/configs/active.yaml` 作为当前生效配置。

## 目录结构速览
- `src/vidsynth/core`: 数据模型、配置、日志、路径工具。
- `src/vidsynth/segment`: Step1 实现（采样、embedding、镜头切分）。
- `src/vidsynth/theme_match`: Step2 实现（主题原型与打分）。
- `src/vidsynth/sequence`: Step3 实现（片段选择与 EDL 合并）。
- `src/vidsynth/export`: Step4 实现（按 EDL 导出 MP4）。
- `configs/`: baseline 及自定义 YAML。
- `scripts/`: 批处理/实验脚本。
- `tests/`: 单元与集成测试，结构与 `src` 镜像。
- `My_docs/MVP_framework.md`: 框架设计目标与阶段说明。
- `My_docs/PROGRESS.md`: 针对 `My_docs/MVP_framework.md` 的阶段进度记录。
- `My_docs/AGENTS.md`: 贡献者指南与项目结构约定。

## 输出产物
- `clips.json`：Step1 片段清单（含时间段、embedding 均值、模型信息）。
- `scores.json`：Step2 主题得分（含 `score/s_pos/s_neg`）。
- `edl.json`：Step3 合并后的剪辑列表。
- `output.mp4`：Step4 导出成片。
