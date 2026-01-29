# VidSynth Workspace（工作区）说明

此目录用于存放运行时资源与生成产物。后端 FastAPI（后端框架）会将该目录挂载到 `/static`，前端通过 URL（地址）读取文件，无需经由 API（接口）传输大体积数据。

如需调整路径，请在启动服务前设置环境变量 `VIDSYNTH_WORKSPACE_ROOT`。

## 目录结构

```
workspace/
  videos/                          # 输入视频（video_id 为文件名去后缀）
  gt/                              # GT（Ground Truth，标注）JSON（与 video_id 同名）
  thumbnails/                      # 视频封面缩略图（thumbnail）
  configs/                         # Settings（配置）覆盖与运行态快照
    active.yaml                    # 当前生效配置
    override.yaml                  # 覆盖配置
    secrets.json                   # 密钥配置（不入库）
  segmentation/{video_id}/         # Stage 1（阶段一）产物
    clips.json                     # 切分列表
    status.json                    # Stage 1 状态
    thumbs/                        # 片段缩略图（供 Stage 2 UI 使用）
  themes/{theme_slug}/             # Stage 2（阶段二）产物
    scores.json                    # 主题打分结果
    status.json                    # Stage 2 状态
  edl/{theme_slug}/                # Stage 3（阶段三）产物
    edl.json                       # EDL（Edit Decision List，剪辑决定列表）
    status.json                    # Stage 3 状态
  exports/{theme_slug}/            # Stage 4（阶段四）产物
    output.mp4                     # 最终输出视频
    status.json                    # Stage 4 状态
```

## 注意事项

- `video_id` 来自视频文件名（去后缀）。
- `theme_slug` 是主题名的 sanitize（清洗）结果，用作目录键。
- 产物默认可缓存（cache），如需重算请在 API（接口）中传入 `force`。
- 该目录默认被 `.gitignore` 忽略，仅保留必要的占位文件与说明文档。
