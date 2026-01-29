# VidSynth 本地前后端统一设计（共用文件系统）

> 目标：在不改变现有代码架构的前提下，利用共用文件系统 + 轻量 API/SSE，把现有 UI 与后端能力打通，服务技术开发者的本地验证场景。

## 1. 核心原则
- **共用文件系统**：所有大数据（视频、clips、scores、edl、导出 mp4）存放在统一工作区，前后端通过路径传递引用，不传输视频数据。
- **静态访问 + 命令接口**：后端挂载 `/static` 暴露工作区，API 只负责下发命令/元数据，SSE 负责状态流。
- **可缓存、可重跑**：所有阶段支持缓存复用与 `force` 重算；当源文件更新需失效缓存。
- **多视频、多主题**：以 `video_id` 和 `theme_slug` 为命名基准，所有产物可并存。

## 0. 项目整体框架
- 现有根目录（简化）：
```
VidSynth/
  README.md
  MVP_framework.md
  PROGRESS.md
  cluster.md
  src/vidsynth/            # Python 核心库与 server（服务端）
  configs/                 # baseline 配置
  scripts/                 # 辅助脚本
  tests/                   # 单测
  VidSynth-Visualizer/     # React 前端（Vite）
  assets/                  # 示例资源（可选）
  STAGE*_PLAN.md           # 阶段设计文档
  UNIFIED_SYSTEM_DESIGN.md # 本文档
```
- 新增/共用工作区（默认放在根目录 `workspace/`，可通过环境变量配置路径）：
```
workspace/
  videos/                         # Stage0：原始视频
  gt/                             # Stage0：GT JSON（同名）
  thumbnails/                     # Stage0：封面缓存
  segmentation/{video_id}/clips.json            # Stage1
  themes/{theme_slug}/scores.json               # Stage2
  edl/{theme_slug}/edl.json                     # Stage3
  exports/{theme_slug}/output.mp4               # Stage4
```
- 工作区根目录可通过环境变量 `VIDSYNTH_WORKSPACE_ROOT` 覆盖，默认使用项目根目录下的 `workspace/`。

## 2. 工作区目录（建议）
```
workspace/
  videos/                         # Stage0：原始视频（手动放置或导入）
  gt/                             # Stage0：同名 GT JSON
  thumbnails/                     # Stage0：自动抽帧生成封面
  segmentation/{video_id}/clips.json            # Stage1：切分结果
  themes/{theme_slug}/scores.json               # Stage2：主题打分结果（含 video_id 字段）
  edl/{theme_slug}/edl.json                     # Stage3：片段选择/合并结果
  exports/{theme_slug}/output.mp4               # Stage4：导出视频
```
- 后端挂载 `/static` 指向 `workspace`；前端用 `/static/...` 直接读取。
- `theme_slug` 需对用户输入主题做 sanitize（空格/特殊字符替换为 `_`）。

## 3. 统一 API 与数据流（按阶段）

### 3.1 Stage0 素材管理
- `GET /api/assets`
  - 扫描 `videos/`，匹配同名 `gt/`、`segmentation/` 产物。
  - 返回字段示例：`{ video_id, name, video_url, gt_url|null, thumb_url|null, duration, has_gt, segmented, clips_url|null }`
- `POST /api/import/videos`：上传视频文件流，写入 `workspace/videos/`。
- `POST /api/gt/upload {video_id, file}`：补充/覆盖 GT。
- `POST /api/assets/rescan`：触发重新扫描（适配手工放文件）。

### 3.2 Stage1 片段切分（Segmentation）
- `POST /api/segment {video_ids:[], force?:bool}`：未切分→执行；已切分且 !force → 直接标记 cached。
- `GET /api/segments/{video_id}`：返回 `clips.json`。
- 产物：`segmentation/{video_id}/clips.json`。

### 3.3 Stage2 主题匹配（Theme Matching）
- `POST /api/theme/expand {theme_text}` → 返回 `positives[]/negatives[]`（LLM 生成，可编辑）。
- `POST /api/theme/analyze {theme, positives?, negatives?, video_ids?, force?}`：遍历 clips 计算分数，支持缓存复用。
- `GET /api/theme/{theme_slug}/result`：返回 `scores.json`。
- 产物：`themes/{theme_slug}/scores.json`，包含 `meta`（theme、prototypes、emb_model 等）与 `scores`（按 video_id 分组的 clip 分数）。

### 3.4 Stage3 片段筛选/编排（Sequencer）
- `POST /api/sequence {theme, upper?, lower?, min_seconds?, max_seconds?, force?, video_ids?}`：基于 scores 阈值筛选并合并连续片段，生成 EDL；缓存可复用。
- `GET /api/sequence/{theme_slug}/edl`：返回主题 EDL。
- 产物：`edl/{theme_slug}/edl.json`，字段 `video_id, t_start, t_end, reason`。

### 3.5 Stage4 导出（Export）
- `POST /api/export {theme, video_id, edl_path?, source_video_path?, force?}`：按 EDL 拼接单源视频（MVP）；可未来扩展多源。
- `GET /api/export/{theme_slug}`：查询导出状态/路径。
- 产物：`exports/{theme_slug}/output.mp4`。

## 4. SSE 统一事件协议
- Endpoint：`/api/events`（复用全流程）
- 事件载荷建议：
```json
{
  "stage": "segment|theme_match|sequence|export",
  "theme": "skiing",
  "video_id": "video_A",
  "status": "queued|running|cached|done|error",
  "progress": 0.0,          // 可选 0-1
  "message": "human readable",
  "result_path": "themes/skiing/scores.json"     // 视阶段返回 clips/edl/output 路径
}
```
- 错误需推送 `status=error` 与 `message`，前端终止 Loading 并提示。

## 5. 前端对接要点（不改主体框架）
- **资源加载**：启动时 `GET /api/assets` 填充 `VideoResource`（url/thumbnail/hasGT/segmented/duration）。
- **Stage0**：ProjectConfigModal 支持多选/全选；缺失 GT 显示灰色占位，可点击补传；可触发 rescan。
- **Stage1**：若 `segmented=false` 显示空态按钮触发 `POST /api/segment`；已切分直接加载 `clips.json` 映射到 PRED 轨道。
- **Stage2**：主题输入 + Expand → 编辑原型 → Start Analysis 调用 `analyze`，监听 SSE；完成后加载 `scores.json` 渲染热力图/TopK。
- **Stage3**：参数面板调用 `sequence`，日志/进度用 SSE，完成后刷新 EDL 列表。
- **Stage4**：播放器指向 `/static/exports/.../output.mp4`，EDL 列表来自 `GET /api/sequence/.../edl`，点击跳转播放。
- **缓存提示**：后端若返回/推送 `cached`，前端显示“已存在结果，可选择重跑 (force)”。

## 6. 特殊注意
- **embedding 后端**：若 clips 使用 `mean_color`，主题打分将为 0，需在后端检测并返回警告；前端提示需用 openclip 重跑。
- **时长兜底**：后端扫描时填充 `duration`（ffprobe）；前端 `onLoadedMetadata` 二次兜底。
- **失效处理**：若视频/GT/clips 被替换，需让后端判定缓存失效（mtime/hash）或依赖前端 `force` 重跑。
- **命名冲突**：相同主题多次计算需明确覆盖策略（force）或增加版本号；`theme_slug` 必须可逆映射到原始主题名。

## 7. 最小落地路线
1) 落地工作区与 `/static`，实现 `GET /api/assets` 与扫描状态。
2) 打通 Stage1 `POST /api/segment` + SSE 状态；前端 Step1 用真实 clips 替换模拟。
3) 接 Stage2 `expand/analyze` + SSE，前端热力图用真实 scores。
4) 接 Stage3/4 `sequence/export`，前端日志/播放器/EDL 列表接真实数据。
