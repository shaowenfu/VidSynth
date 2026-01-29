# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令 (Common Commands)

### 环境设置
```bash
python -m venv venv && source venv/bin/activate
pip install -e .[dev]
pre-commit install
```

### 后端开发
```bash
# 启动 FastAPI 服务器 (默认端口 8000)
uvicorn vidsynth.server.app:app --reload

# 运行测试
pytest                       # 运行全部测试
pytest tests/segment/        # 运行特定目录测试
pytest -k "test_segment"     # 运行匹配的测试
pytest --cov=src/vidsynth    # 生成覆盖率报告

# 代码检查与格式化
ruff check src/ tests/       # lint 检查
black src/ tests/            # 格式化代码
```

### 前端开发 (VidSynth-Visualizer)
```bash
cd VidSynth-Visualizer
npm install                  # 首次安装依赖
npm run dev                  # 启动 Vite 开发服务器 (默认端口 5173)
npm run build                # 构建生产版本
```

### 辅助脚本
```bash
# 创建测试数据
python scripts/create_dummy_test_data.py

# 端到端 pipeline 测试
python scripts/e2e_full_pipeline_test.py

# 开发环境一键启动 (前端 + 后端)
bash scripts/dev_start.sh
```

## 项目架构 (Project Architecture)

VidSynth 是一个主题驱动的多源视频自动编排 MVP，核心流程分为 4 个 Stage：

```
Stage0 (素材管理) → Stage1 (片段切分) → Stage2 (主题匹配) → Stage3 (片段筛选) → Stage4 (导出成片)
```

### 后端结构 (Python)

```
src/vidsynth/
├── core/           # 数据模型 (Clip, VideoAsset)、配置 (PipelineConfig)、日志、路径工具
├── segment/        # Stage1 实现: 采样、embedding、镜头切分
├── theme_match/    # Stage2 实现: 主题原型生成 (LLM)、零样本打分
├── sequence/       # Stage3 实现: Sequencer (阈值筛选 + 连续片段聚合生成 EDL)
├── export/         # Stage4 实现: Exporter (按 EDL 拼接 MP4, 音频淡入淡出)
├── server/         # FastAPI 应用、SSE 事件推送、静态文件挂载
│   ├── routers/    # API 路由: assets, segment, theme, sequence, export, settings
│   ├── tasks.py    # 串行任务队列与状态持久化
│   └── events.py   # SSE 事件广播器
└── cluster/        # 集群/批处理脚本
```

**关键设计原则**:
- **共用文件系统**: 所有大数据 (视频、clips、scores、edl、mp4) 存放在 `workspace/` 目录，前后端通过路径传递引用
- **SSE 统一事件协议**: `/api/events` 推送 `stage/status/progress/result_path`
- **可缓存、可重跑**: 所有阶段支持缓存复用与 `force` 重算

### 前端结构 (React + TypeScript)

```
VidSynth-Visualizer/
├── components/
│   ├── ProjectConfigModal.tsx    # 素材管理对话框 (Stage0)
│   ├── Step1Segmentation.tsx     # 片段切分可视化 (Stage1)
│   ├── Step2Semantic.tsx         # 主题匹配与热力图 (Stage2)
│   ├── Step3Log.tsx              # 策略日志 (Stage3)
│   └── Step4FinalCut.tsx         # 最终成片播放器 (Stage4)
├── App.tsx                       # 主应用，管理 SSE 连接
└── types.ts                      # 共享类型定义
```

### 工作区布局 (workspace/)

```
workspace/
├── videos/                         # Stage0: 原始视频
├── gt/                             # Stage0: GT JSON (同名)
├── thumbnails/                     # Stage0: 封面缓存
├── segmentation/{video_id}/clips.json    # Stage1: 切分结果
├── themes/{theme_slug}/scores.json       # Stage2: 主题打分结果
├── edl/{theme_slug}/edl.json             # Stage3: 剪辑列表
└── exports/{theme_slug}/output.mp4       # Stage4: 导出视频
```

**环境变量**:
- `VIDSYNTH_WORKSPACE_ROOT`: 工作区根目录 (默认项目根目录下 `workspace/`)
- `VIDSYNTH_STORAGE_ROOT`: 大容量存储根目录 (默认 `assets/`)
- `VIDSYNTH_CONFIG_PATH`: 配置文件路径 (默认 `configs/baseline.yaml`)
- `.env` 文件: 敏感配置 (如 `DEEPSEEK_API_KEY`) 自动加载

### 配置系统

- **配置文件**: `configs/baseline.yaml`
- **配置类**: `src/vidsynth/core/config.py` (SegmentConfig, ThemeMatchConfig, ExportConfig, EmbeddingConfig)
- **运行时更新**: `/api/settings` 写入 `workspace/configs/active.yaml`
- **Embedding 后端**: 支持 `mean_color` (CPU fallback) 和 `open_clip` (GPU/CPU)

### 任务系统

- **TaskManager**: 单工作线程串行队列 (`src/vidsynth/server/tasks.py`)
- **状态持久化**: `workspace/tasks/status.json`
- **状态值**: `queued | running | cached | done | error`

### SSE 事件协议

```json
{
  "stage": "segment|theme_match|sequence|export",
  "theme": "theme_slug",
  "video_id": "video_id",
  "status": "queued|running|cached|done|error",
  "progress": 0.0,
  "message": "human readable",
  "result_path": "themes/skiing/scores.json"
}
```

## API 路由速览

| 路由 | 用途 |
|------|------|
| `GET /api/assets` | 扫描工作区，返回视频资源列表 |
| `POST /api/import/videos` | 上传视频到 `workspace/videos/` |
| `POST /api/segment` | 触发 Stage1 切分任务 |
| `GET /api/segments/{video_id}` | 获取 `clips.json` |
| `POST /api/theme/expand` | LLM 生成主题原型 (positives/negatives) |
| `POST /api/theme/analyze` | 触发 Stage2 主题分析任务 |
| `GET /api/theme/{theme_slug}/result` | 获取 `scores.json` |
| `POST /api/sequence` | 触发 Stage3 编排任务 (生成 EDL) |
| `GET /api/sequence/{theme_slug}/edl` | 获取 EDL 列表 |
| `POST /api/export` | 触发 Stage4 导出任务 (生成 MP4) |
| `GET /api/export/{theme_slug}` | 查询导出状态 |
| `GET /api/settings` | 获取当前配置 |
| `PUT /api/settings` | 更新配置 |
| `GET /api/events` | SSE 事件流 |
| `/static/*` | 静态文件访问 (指向 workspace/) |

## 开发注意事项

1. **不要删除小片段**: Stage1 切分保留所有片段，前端负责筛选展示
2. **mean_color 回退**: 当 embedding backend 为 mean_color 时，主题打分将返回 0，需在前端提示用户重跑
3. **theme_slug sanitize**: 主题输入需做 sanitize (空格/特殊字符替换为 `_`)
4. **缓存失效**: 源文件更新需手动 `force` 重跑，或依赖 mtime/hash 检测
5. **日志系统**: 使用 `vidsynth.core.logging_utils.get_logger()`，SSE 会自动捕获 INFO 级别日志
6. **命名一致性**: `video_id` 和 `theme_slug` 是所有产物命名基准
