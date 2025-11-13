# Step1 功能验证指导（片段切分）

> 参考 `develop_docs/MVP_framework.md` 的 Step1 目标：确保“视频采集 → 关键帧抽样 → embedding → 镜头切分 → Clip JSON 导出”在本仓库内可完整复现并通过测试。

## 1. 视频收集阶段

### 1.1 素材规格建议
| 指标 | 建议值 | 说明 |
| --- | --- | --- |
| 分辨率 | 1280×720～3840×2160 | Step1 抽帧逻辑基于 OpenCV，推荐 720p/1080p，4K 需关注 IO；低于 480p 会削弱 embedding 稳定性。 |
| 编码格式 | MP4 (H.264 + AAC) | `cv2.VideoCapture` 对 MP4/H.264 最稳定；非常规编码需自行安装解码器。 |
| 帧率 | ≥24 fps，恒定帧更佳 | 关键帧抽样以 1fps 为基准，过低帧率会导致时间戳不准；高帧率自动按整数间隔取样。 |
| 时长 | 单视频 15s–10min | 片段切分默认输出 2–6 秒片段；超长视频建议先手动粗分段。 |
| 画面特性 | 光照/运动变化真实 | 镜头切分依赖 embedding + HSV 直方图；持续静帧可能被合并，需要在 checklist 中手动核验。 |

### 1.2 存储与命名
- 将原始文件置于 `assets/raw/<主题>/<video_id>.mp4`，或设置 `VIDSYNTH_STORAGE_ROOT` 指向大容量磁盘。
- 维护一个 `scripts/video_manifest.csv`（可选），字段包含 `video_id,path,theme,note`，便于批处理脚本遍历。
- 保留素材元信息（分辨率、拍摄设备）以便调试阈值；建议同步记录在 `docs/data_logs/<date>.md`（可按需新建）。

## 2. 数据处理流程

```mermaid
flowchart LR
  A[视频素材 ready] --> B[iter_keyframes 抽帧]
  B --> C[EmbeddingBackend 生成帧特征]
  C --> D[detect_shots 计算切点]
  D --> E[build_clips_from_samples 合并/拆分]
  E --> F[Clip JSON 导出 (CLI)]
```

| 步骤 | 入口命令/模块 | 输入 | 关键配置 | 产出 |
| --- | --- | --- | --- | --- |
| 1. 环境准备 | `python -m venv venv && source venv/bin/activate`<br>`pip install -e .[dev]` | 代码仓 | `pyproject.toml` | 本地可执行环境 |
| 2. 配置确认 | `configs/baseline.yaml` + `docs/CONFIG_CLI.md` | YAML / 环境变量 | `segment.*`、`embedding.*` | 运行所需参数，记录到实验日志 |
| 3. CLI 运行 | `vidsynth segment-video <video> -o out/clips.json --config configs/baseline.yaml` | 单个 MP4 | `SegmentConfig`, `EmbeddingConfig` | `clips.json`（Clip 列表） |
| 4. 结果验证 | `jq '.[0]' out/clips.json` / 可视化脚本 | `clips.json` | 无 | 观察 `t_start/t_end/vis_emb_avg` 合理性 |
| 5. 批处理（可选） | `scripts/batch_segment.sh`（自建） | `video_manifest.csv` | CLI 参数 | 多个 JSON，路径记录于 manifest |

额外提示：
- CPU 主机优先使用 `embedding.backend=mean_color` 或 `open_clip+cpu-small`，避免推理瓶颈；GPU 主机可通过 `--embedding-backend open_clip --embedding-preset gpu-large --embedding-device cuda` 解锁更高精度。
- `SegmentConfig.merge_short_segments` 与 `split_long_segments` 已默认开启，用于维持 2–6 秒范围；需要极短片段时可在自定义 YAML 中关闭。

## 3. 功能测试方案

### 3.1 测试环境搭建
1. 克隆仓库并安装开发依赖：`pip install -e .[dev]`。
2. 可选依赖：`pip install open-clip-torch pillow`（若需真实 embedding）；若无 GPU，可保持 baseline。
3. 设置必要环境变量：  
   ```bash
   export VIDSYNTH_CONFIG_PATH=$(pwd)/configs/baseline.yaml
   export VIDSYNTH_STORAGE_ROOT=$(pwd)/assets
   ```

### 3.2 测试用例矩阵
| 测试类型 | 覆盖文件 | 关注点 | 运行命令 | 预期 |
| --- | --- | --- | --- | --- |
| 单元：切分边界 | `tests/segment/test_shot_detector.py` | 余弦/直方图阈值是否正确触发切点 | `pytest tests/segment/test_shot_detector.py` | 输出的 `(start,end)` 与构造场景一致 |
| 单元：片段合并/拆分 | `tests/segment/test_clipper.py` | `merge_short_segments`、`split_long_segments` 行为 | `pytest tests/segment/test_clipper.py` | Clip 数量、长度满足配置 |
| 集成：端到端切分 | `tests/segment/test_segment_pipeline.py` | `segment_video` 流水串联正确 | `pytest tests/segment/test_segment_pipeline.py` | 得到 2 个 Clip、无丢弃段 |
| CLI：JSON 导出 | `tests/test_cli.py` | Typer 参数解析、文件写入 | `pytest tests/test_cli.py` | CLI 返回码 0，输出 JSON 含 1 个 Clip |
| 手工：真实视频 | 自备 mp4 | OpenCV + 嵌入器实际运行 | `vidsynth segment-video assets/raw/demo.mp4 -o out/demo_clips.json` | 日志显示片段数量，JSON 中 `vis_emb_avg` 与模型匹配 |

### 3.3 预期输出与判定
- `clips.json` 每个元素应包含 `video_id / clip_id / t_start / t_end / fps_keyframe / vis_emb_avg / emb_model / created_at / version`。示例：
  ```json
  {
    "video_id": "demo",
    "clip_id": 0,
    "t_start": 0.0,
    "t_end": 4.8,
    "fps_keyframe": 1.0,
    "vis_emb_avg": [0.12, 0.88, 0.32],
    "emb_model": "openclip::ViT-B-32::laion400m_e32",
    "created_at": "2024-05-10T12:34:56.123456+00:00",
    "version": 1
  }
  ```
- 关键判定标准：
  1. **时间连续性**：`clip_id` 递增，每段 `t_end > t_start` 且落在视频时长范围内。
  2. **嵌入来源**：`emb_model` 与 CLI/配置一致（mean_color 或 openclip 预设）。
  3. **片段长度**：绝大部分落在 `SegmentConfig.min/max` 范围；如出现极短片段，需要检查原视频是否存在静帧或手动调整阈值。
  4. **丢弃统计**：CLI 日志或 `SegmentResult.discarded_segments` 应接近 0；大于 0 时需检查 `split/merge` 是否被禁用或阈值过低。

## 4. 检查清单（进入 Step2 前必查）
- [ ] 素材按表格规格采集并落盘至 `assets/raw/`，记录 `video_id` 与主题。
- [ ] `configs/baseline.yaml` 经确认适合当前素材；如有改动，已同步更新 `docs/CONFIG_CLI.md` 与实验记录。
- [ ] CLI 在代表性视频（至少 3 条不同场景）上跑通，输出 JSON 已归档在 `out/<video_id>/clips.json`。
- [ ] `pytest`（至少覆盖 `tests/segment` 与 `tests/test_cli.py`）全部通过；如引入 OpenCLIP，也在 GPU/CPU 模式下各跑一次。
- [ ] 样例 `clips.json` 已人工 spot-check（查看 2–3 个片段时间戳与画面是否吻合）。
- [ ] 运行日志及 CLI 命令写入 `docs/PROGRESS.md` 或团队共享记录，便于他人复现。

完成上述步骤后，即可将 `clips.json` 作为 Step2 主题匹配模块的输入，保证后续开发基于可靠的切分结果。

