### Stage 0: 素材管理 (Project Configuration Modal) 方案

为了实现前端的 Project Configuration 面板（对应 `VidSynth-Visualizer/components/ProjectConfigModal.tsx`）的预期功能，我们需要在文件系统层面和前后端 API 交互层面进行设计。

#### 1. 文件系统规划 (File System Strategy)

为了满足 **“固定路径自动加载”** 和 **“文件名匹配”** 的需求，同时兼顾 B/S 架构限制与静态资源托管便利性，我们将统一工作区结构优化如下。此目录应被 `.gitignore` 忽略。

**建议的 `workspace/` 目录结构（可通过环境变量 `VIDSYNTH_WORKSPACE_ROOT` 覆盖）：**

```
VidSynth/
├── workspace/                  # [新增] 统一工作区
│   ├── videos/                 # [固定路径] 存放所有原始视频 (.mp4, .mov 等)
│   │   ├── video_A.mp4
│   │   └── video_B.mp4
│   ├── gt/                     # [固定路径] 存放对应的 Ground Truth 文件 (.json) - 原 jsons/
│   │   ├── video_A.json        # 必须与视频同名（不含后缀）
│   │   └── video_B.json
│   ├── thumbnails/             # [自动生成] 存放视频封面缓存 (.jpg) - 取消隐藏以便静态托管
│       ├── video_A.jpg
│       └── video_B.jpg
│   └── segmentation/           # [Stage1] 存放切分结果
│       ├── video_A/
│       │   └── clips.json
│       └── video_B/
│           └── clips.json
└── src/...
```

**核心规则：**
*   **文件名即ID**: 系统将通过文件名（不含后缀）来关联 `videos/` 目录下的视频文件和 `gt/` 目录下的 JSON 文件。
*   **静态托管**: 后端将 `workspace/` (或其子目录) 挂载为静态资源路径，例如 `/static/videos/` 和 `/static/thumbnails/`，供前端直接访问。

---

#### 2. 详细逻辑与实施步骤 (前后端对齐)

##### 步骤 A: 后端 API 设计 (FastAPI)

后端提供以下接口支持资源管理：

1.  **`GET /api/assets` (获取资源列表)**
    *   **职责**: 返回 `workspace/` 中所有视频及其关联资源的完整 URL。
    *   **逻辑**: 
        1.  **扫描**: 遍历 `workspace/videos/`。
        2.  **匹配**: 检查 `gt/{id}.json` 是否存在。
        3.  **切分状态**: 检查 `segmentation/{id}/clips.json` 是否存在，若存在则 `segmented=true`。
        4.  **缩略图**: 检查 `thumbnails/{id}.jpg`，不存在则实时生成。
        5.  **时长**: 若缓存中无时长信息，则读取视频元数据填充。
        6.  **构建URL**: 返回可直接访问的静态资源 URL。
    *   **返回示例**:
        ```json
        [
          {
            "id": "video_A",
            "name": "video_A.mp4",
            "duration": 120,
            "hasGT": true,
            "segmented": true,                               // [新增] 是否已切分
            "video_url": "/static/videos/video_A.mp4",
            "thumb_url": "/static/thumbnails/video_A.jpg",
            "gt_url": "/static/gt/video_A.json",
            "clips_url": "/static/segmentation/video_A/clips.json",       // [新增] 切分结果 URL
            "status": "done"
          }
        ]
        ```

2.  **`POST /api/import/videos` (导入视频)**
    *   **职责**: 接收前端文件流，写入 `workspace/videos/`。
    *   **适用场景**: 标准 B/S 模式上传（Localhost 下速度极快，体验接近复制）。
    *   **逻辑**: 保存文件 -> 生成缩略图 -> 返回更新后的资源列表。

3.  **`POST /api/gt/upload` (导入 GT JSON)**
    *   **输入**: `form-data` 携带 `{video_id, file}`。
    *   **职责**: 接收 JSON 文件流，写入 `workspace/gt/{video_id}.json`。
    *   **逻辑**: 强制重命名以匹配视频 ID -> 返回成功状态。

4.  **`POST /api/assets/rescan` (手动刷新)**
    *   **职责**: 重新扫描 `workspace/` 目录。
    *   **适用场景**: 用户手动将文件复制到文件夹中，或者点击 "Sync JSONs" 按钮尝试自动匹配新放入的文件。

##### 步骤 B: 前端改造逻辑 (`VidSynth-Visualizer/components/ProjectConfigModal.tsx`)

1.  **加载资源**:
    *   组件挂载时调用 `GET /api/assets`。
    *   使用返回的 `thumb_url` 渲染封面，`hasGT` 渲染状态。

2.  **“Add Sources” 按钮**:
    *   **行为**: 触发文件选择 -> 调用 `POST /api/import/videos` (流式上传)。点击此按钮应触发一个隐藏的 `<input type="file" multiple accept="video/*" />`元素，允许用户选择多个视频文件。
    *   **说明**: 这是最通用的方式，兼容所有浏览器环境。
    *   **上传成功后**，再次调用 `GET /api/assets` 刷新 `videos` 列表，以显示新添加的视频及其状态。

3.  **GT Registry 交互**:
    *   **现有问题**: 右侧 JSON 状态的小方格 `div` 目前没有 `onClick` 事件，无法触发用户上传缺失的JSON 文件。
    *   **单个格子点击**: 点击灰色的格子 -> 文件选择 -> 调用 `POST /api/import/gt/{video_id}`。
    *   **“Sync JSONs” 按钮**:
        *   **行为**: 调用 `POST /api/rescan`。
        *   **目的**: 允许用户“手动放入文件后刷新”，作为流式上传的补充手段。

4.  **静态资源访问**:
    *   前端不再需要处理本地路径，直接使用 API 返回的 `/static/...` 相对路径即可。

---

#### 流程图总结

```mermaid
graph TD
    subgraph Frontend
        A[GET /api/assets] --> B{渲染 Grid}
        C[Add Sources] --> D[POST /api/import/videos]
        E[Click GT Grid] --> F[POST /api/import/gt/{id}]
        G[Sync JSONs] --> H[POST /api/rescan]
    end

    subgraph Backend
        H --> I[扫描 workspace]
        I --> J[构建静态 URLs]
        J --> A
        D --> K[写入 workspace/videos]
        K --> L[生成 Thumbnail]
        F --> M[写入 workspace/gt]
    end
```
