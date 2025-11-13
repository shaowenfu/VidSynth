# VidSynth 配置与 CLI 指南

## baseline.yaml 字段说明
- `segment.fps_keyframe`：关键帧抽帧速率（默认 1fps），越大越稠密，代价更高。
- `segment.cosine_threshold` / `segment.histogram_threshold`：镜头切分阈值；前者基于 CLIP embedding 余弦距离，后者基于 HSV 直方图。调低会产生更多切点。
- `segment.min_clip_seconds` / `segment.max_clip_seconds`：片段允许的时间范围，单位秒。`merge_short_segments` 控制是否自动合并不足 `min` 的连续段，`keep_last_short_segment` 为 `False` 时会丢弃尾段。`split_long_segments` 为 `True` 时会按 `max` 切割长镜头。
- `theme_match`：预留给 Step3 的打分阈值（`score_threshold`）和负样本权重（`negative_weight`），即使当前未使用也保持与 MVP 描述一致，方便后续衔接。
- `export`：导出参数（编码器、码率、音频/视频淡入淡出时间），目前 clipper 仅填充元信息，未来拼接阶段将消费这些值。
- `embedding`：
  - `backend`：`mean_color`（轻量占位，零依赖）或 `open_clip`（真实视觉 embedding）。
  - `preset`：`cpu-small`（ViT-B/32+laion400m，适合 CPU）或 `gpu-large`（ViT-H/14+laion2b，需高端 GPU）。设置后会覆盖 `model_name`/`pretrained`。
  - `device`：`cpu` 或 `cuda`/`cuda:0` 等；同时可通过环境变量 `VIDSYNTH_EMBEDDING_DEVICE` 覆盖。
  - `precision`：`fp32` 或 `amp`。当设备为 GPU 且设为 `amp` 时会使用半精度推理。

### 环境变量覆盖
- `VIDSYNTH_CONFIG_PATH`：指向自定义 YAML。
- `VIDSYNTH_SEGMENT_FPS`、`VIDSYNTH_THEME_SCORE_THRESHOLD`：针对单独字段的快速调整。
- `VIDSYNTH_EMBEDDING_BACKEND` / `VIDSYNTH_EMBEDDING_DEVICE`：在 CI 或脚本中切换 embedding 模式。
- `VIDSYNTH_STORAGE_ROOT`：素材根目录，覆盖 `assets_root`。

## CLI 使用方式
CLI 入口位于 `src/vidsynth/cli.py`，安装依赖后可通过两种方式调用：

```bash
# 方式一：python -m
python -m vidsynth.cli segment-video data/raw/demo.mp4 \
  --output out/demo_clips.json \
  --config configs/baseline.yaml

# 方式二：安装后使用脚本名
vidsynth segment-video data/raw/demo.mp4 -o out/demo.json
```

### 常用参数
- `--video-id`：自定义 `Clip.video_id`，默认取文件名。
- `--config`：指定非默认配置文件。
- `--embedding-backend` / `--embedding-preset` / `--embedding-device`：命令行覆盖 embedding 设置，例如 `--embedding-backend open_clip --embedding-preset gpu-large --embedding-device cuda`.
- `--log-level`：控制日志输出。
- `--output`：Clip JSON 写入路径，默认 `clips.json`。

### 典型场景
1. **CPU 试跑**：使用默认 baseline，`mean_color` 或 `open_clip` + `cpu-small`。
   ```bash
   vidsynth segment-video sample.mp4 --output tmp/clips.json
   ```
2. **GPU 高精度**：自定义配置或直接指定参数。
   ```bash
   vidsynth segment-video sample.mp4 \
     --embedding-backend open_clip \
     --embedding-preset gpu-large \
     --embedding-device cuda \
     --output tmp/clips_gpu.json
   ```
3. **批量脚本**：在 shell 中设置环境变量再调用 CLI，可避免频繁写参数。
   ```bash
   export VIDSYNTH_EMBEDDING_BACKEND=open_clip
   export VIDSYNTH_EMBEDDING_DEVICE=cuda
   python -m vidsynth.cli segment-video videos/case1.mp4 -o out/case1.json
   ```

保持 baseline 的简洁意味着任何新增阈值或开关都应同时更新此文件及本文档，方便贡献者快速理解和复现。
