# VidSynth Visualizer 项目结构分析

## 快速概览
- 定位：基于 React 19 + TypeScript + Vite 的前端原型，用静态/随机生成的数据演示“视频智能处理流水线”的各阶段体验。
- 视图切换：`App.tsx` 在 “Main Pipeline” 与 “Cluster Sandbox” 两种视图间切换，并控制项目配置模态框。
- 数据来源：全部为前端 mock（`constants.ts` 中的 `MOCK_VIDEOS`、`MOCK_LOGS`、`generateSegments`、`generateClusterPoints`）；无真实后端请求。
- 样式体系：Tailwind CDN 直接在 `index.html` 注入，组件使用类字符串；少量自定义样式（滚动条）。
- 依赖面：核心仅 `react`/`react-dom`、`lucide-react` 图标、`recharts` 可视化；无状态管理库和测试框架。

## 构建与运行
- 包管理与脚本：`npm install`，`npm run dev`（默认 3000 端口，已在 `vite.config.ts` 配置 host 0.0.0.0）、`npm run build`、`npm run preview`。
- 环境变量：`vite.config.ts` 将 `GEMINI_API_KEY` 暴露到 `process.env`；需在 `.env.local` 配置但当前功能未调用。
- TypeScript：`tsconfig.json` 采用 Vite 的 bundler 解析、`jsx: react-jsx`，无严格编译输出（`noEmit`）。

## 目录与职责
- `App.tsx`：顶层状态（当前视频、视频列表、当前视图、模态开关），分发到各步骤组件；包含头部导航与 Project Config 入口。
- `components/Step1Segmentation.tsx`：分割实验室，展示视频播放器、GT vs 预测时间轴、JSON 视图、分析侧栏；内置执行模拟（定时器驱动进度与结果）。
- `components/Step2Semantic.tsx`：语义雷达。将所有视频的 `predictedSegments` 扁平化为全局时间线热力条与横向卡片列表；含分析进度模拟与悬浮提示。
- `components/Step3Log.tsx`：策略日志黑盒。带参数面板与日志终端，定时模拟日志流与进度条。
- `components/Step4FinalCut.tsx`：最终剪辑预览 + EDL 列表（静态占位、使用 Picsum 缩略图）。
- `components/ClusterSandbox.tsx`：聚类沙盒，全屏 Recharts 散点图（t-SNE 风格投影）、侧边控制与集群卡片。
- `components/ProjectConfigModal.tsx`：项目配置模态，展示视频资源池和 GT 映射状态，触发批量 “Sync JSONs” 模拟。
- `components/TopBar.tsx`：早期的顶部资源池/GT 条，当前未在 `App.tsx` 中使用。
- 其他：`constants.ts`（mock 生成与示例标签）、`types.ts`（数据模型）、`index.tsx`/`index.html`（Vite 入口）、`metadata.json` 与 `GEMINI.md`（元信息与说明）。

## 状态与数据流
- 统一状态集中在 `App.tsx`：`activeVideoId`、`videos`、`currentView`、`isProjectConfigOpen`。子组件仅通过 props 读写（无全局 store）。
- 数据模拟：
  - `handleUploadGT` 在 `App.tsx` 内部批量标记 `hasGT` 并模拟处理完成（`setTimeout`），同时弹出 alert。
  - 各步骤内部自带模拟进度条与随机数据（Step1 执行器、Step2/Step3 分析进度、ClusterSandbox 随机点云）。
- 交互反馈主要是 UI 级别（高亮、进度、tooltip），没有真实副作用或 API 请求。

## 核心界面分解
- Segmentation Lab（Step1）
  - 视频播放器 + 进度叠层（播放状态本地控制，但视频未绑定 `currentTime`）。
  - 时间轴对比：GT 与预测片段按相对时长渲染；hover 提示显示标签/分数。
  - JSON 视图按 `video.groundTruth` 渲染，缺失时显示空态。
  - 右侧分析卡片为静态可视化（圆环准确率、柱状趋势）。
- Semantic Radar（Step2）
  - 将所有视频预测片段扁平化后构建热力条；颜色根据 `score` 取段。
  - 横向卡片廊展示缩略图、得分、选中状态；scrollIntoView 定位到点击项。
  - 进度模拟与 tooltip 展示正/负得分。
- Strategy Blackbox（Step3）
  - 参数面板支持数值输入；“Run Strategy” 清空并按阶段生成日志。
  - 日志区为自滚动终端风格列表，带类型高亮与扫描线装饰。
- Final Cut（Step4）
  - 主播放器占位 + 底部时间轴控件。
  - EDL 列表为静态八条占位，引用当前视频名称。
- Cluster Sandbox
  - 左侧控制（算法选择、K 值滑杆、运行按钮）、中部散点、右侧集群卡片。
  - 散点来自 `generateClusterPoints` 随机生成，tooltip 展示缩略图与 cluster 信息。
  - 右侧卡片展示随机占比与 Picsum 缩略图，K 值驱动卡片数量。
- Project Config Modal
  - 资源池网格可切换 active 视频；状态徽标/环表示 GT 映射与处理状态。
  - GT registry 网格显示映射数量、调用 `onUploadGT` 模拟批量注入。

## 数据模型与假数据
- `types.ts`：定义 `Segment`、`GroundTruth`、`VideoResource`、`ClusterPoint`、`LogEntry`、`EdlItem` 等；分数字段可选。
- `constants.ts`：
  - `generateSegments`：按持续时间与分数随机生成片段，供 GT 与预测复用。
  - `MOCK_VIDEOS`：7 条视频，含 URL、缩略图、GT/预测片段、状态。
  - `MOCK_LOGS`：初始日志示例。
  - `generateClusterPoints`：按 clusterId 分布随机点并附带缩略图。
  - `SAMPLE_POSITIVE_TAGS`/`SAMPLE_NEGATIVE_TAGS`：示例标签未在 UI 中使用。

## 样式与交互特征
- Tailwind CDN 提供工具类，未通过 PostCSS/Tailwind 配置参与构建（优点：零配置；风险：类名树摇/排序不可控）。
- 全局样式极少（滚动条、body 背景与选中态），动画与阴影均在组件内部通过类名实现。
- UI 以深色、高对比渐变与玻璃态为主，配合 Lucide 图标与动画类（如 `animate-in`、`animate-progress-indeterminate`）。

## 现状评估与后续接入建议
- 原型性质明显：无真实 API、业务逻辑主要为定时器与随机数；缺乏错误处理与边界状态。
- `TopBar` 未被使用，可删除或替换为当前导航；`FinalCut`/EDL、播放器控制均为静态占位。
- 如需落地：
  1) 接入真实后端：替换 `constants.ts` 为 API 调用，梳理状态（可能引入 RTK Query/SWR）；处理加载、失败、空态。
  2) 播放控制与时间轴：绑定 `<video>` 的 timeupdate 事件，与时间轴/片段交互联动。
  3) Cluster/语义分析：改用后端返回的 embeddings/cluster 结果，添加筛选与标签交互。
  4) 配置与任务流：`handleUploadGT` 改为异步请求 + toast，记录任务状态。
  5) 测试与可观测性：引入 Vitest/RTL 做渲染与交互测试；增加类型校验与日志/埋点。
