from __future__ import annotations

# 本模块负责读取 EDL（剪辑列表）并使用 ffmpeg-python 完成：
# 1) 对源视频按段裁剪（视频/音频分别处理）
# 2) 统一时间戳（PTS-STARTPTS），保证拼接后的时间轴从 0 开始
# 3) 音频在每段首尾添加淡入/淡出，避免爆音与硬断
# 4) 将所有段顺序拼接，按配置输出 H.264 MP4

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

import ffmpeg

from vidsynth.core import PipelineConfig


@dataclass(slots=True)
class EDLItemPayload:
    """EDL JSON 的单条记录。

    - video_id: 源视频标识（当前 MVP 简化为单源；多源需扩展为路径）。
    - t_start/t_end: 裁剪起止时间（秒）。
    - reason: 来源标记，便于导出日志与后续可视化。
    """

    video_id: str
    t_start: float
    t_end: float
    reason: str


class Exporter:
    """导出器：负责将 EDL 转为最终 MP4。

    依赖配置 `PipelineConfig.export`：视频编码器、码率、音频淡入淡出时长等。
    """

    def __init__(self, cfg: PipelineConfig) -> None:
        self.cfg = cfg

    def load_edl(self, path: Path) -> List[EDLItemPayload]:
        """读取 EDL JSON 并转换为内部结构。

        要求每条记录包含 `video_id/t_start/t_end` 字段；`reason` 可选。
        """

        data = json.loads(path.read_text(encoding="utf-8"))
        items: List[EDLItemPayload] = []
        for entry in data:
            items.append(
                EDLItemPayload(
                    video_id=str(entry["video_id"]),
                    t_start=float(entry["t_start"]),
                    t_end=float(entry["t_end"]),
                    reason=str(entry.get("reason", "theme_sequence")),
                )
            )
        return items

    def export(self, edl: Sequence[EDLItemPayload], *, source_video: Path, output_path: Path) -> None:
        """执行导出：按 EDL 裁剪并拼接到一个 MP4。

        当前 MVP 简化为单源视频：`source_video` 指向唯一输入；未来多源需在 EDL 中携带路径并为每源建立输入流。
        """

        segments: List[ffmpeg.nodes.FilterNode] = []
        audio_segments: List[ffmpeg.nodes.FilterNode] = []

        input_stream = ffmpeg.input(str(source_video))
        for item in edl:
            # 视频裁剪并重置时间戳，使每段从 0 开始，便于 concat
            v = (
                input_stream.video
                .trim(start=item.t_start, end=item.t_end)
                .setpts("PTS-STARTPTS")
            )
            # 音频裁剪并重置时间戳
            a = (
                input_stream.audio
                .atrim(start=item.t_start, end=item.t_end)
                .asetpts("PTS-STARTPTS")
            )
            # 音频淡入淡出（避免爆音与硬断）
            fade_ms = self.cfg.export.audio_fade_ms
            duration = max(0.0, item.t_end - item.t_start)
            fade_s = fade_ms / 1000.0
            if fade_s > 0.0 and duration >= 2 * fade_s:
                a = a.filter("afade", type="in", start_time=0, duration=fade_s)
                a = a.filter("afade", type="out", start_time=duration - fade_s, duration=fade_s)
            segments.append(v)
            audio_segments.append(a)

        if not segments:
            # 早退出：无段可拼接
            raise ValueError("EDL 为空，无法导出")

        # concat 参数：v=1 表示视频流数量为 1（逐段顺序连接），a=0 表示不处理音频；反之亦然
        vcat = ffmpeg.concat(*segments, v=1, a=0)
        acat = ffmpeg.concat(*audio_segments, v=0, a=1)

        out = ffmpeg.output(
            vcat, acat,
            str(output_path),
            vcodec=self.cfg.export.video_codec,
            video_bitrate=self.cfg.export.video_bitrate,
            acodec="aac",
            audio_bitrate="192k",
        )
        out = ffmpeg.overwrite_output(out)
        out.run(quiet=True)