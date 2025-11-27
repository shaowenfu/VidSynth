from __future__ import annotations

# 本模块负责读取 EDL（剪辑列表）并使用 ffmpeg-python 完成：
# 1) 对源视频按段裁剪（视频/音频分别处理）
# 2) 统一时间戳（PTS-STARTPTS），保证拼接后的时间轴从 0 开始
# 3) 音频在每段首尾添加淡入/淡出，避免爆音与硬断
# 4) 将所有段顺序拼接，按配置输出 H.264 MP4

import json
import os
from dataclasses import dataclass
import tempfile
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

        # 验证输入文件存在
        if not source_video.exists():
            raise FileNotFoundError(f"源视频文件不存在: {source_video}")
        
        # 验证输出目录可写
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(str(output_path.parent), os.W_OK):
            raise PermissionError(f"输出目录不可写: {output_path.parent}")

        # 逐段裁剪到临时文件，再用 concat demuxer 合并，避免巨型 filter_graph 造成内存/线程飙升
        with tempfile.TemporaryDirectory(prefix="vidsynth_edl_") as tmpdir:
            tmpdir_path = Path(tmpdir)
            segment_paths: List[Path] = []
            for idx, item in enumerate(edl):
                duration = max(0.0, item.t_end - item.t_start)
                if duration <= 0:
                    continue

                # 单段输入，使用 -ss/-to 限定解码窗口，减轻资源占用
                segment_input = ffmpeg.input(str(source_video), ss=item.t_start, to=item.t_end)
                v = segment_input.video.setpts("PTS-STARTPTS")
                a = segment_input.audio

                fade_ms = self.cfg.export.audio_fade_ms
                fade_s = fade_ms / 1000.0
                if fade_s > 0.0 and duration >= 2 * fade_s:
                    a = a.filter("afade", type="in", start_time=0, duration=fade_s)
                    a = a.filter("afade", type="out", start_time=duration - fade_s, duration=fade_s)

                seg_path = tmpdir_path / f"segment_{idx:04d}.mp4"
                seg_output = ffmpeg.output(
                    v,
                    a,
                    str(seg_path),
                    vcodec=self.cfg.export.video_codec,
                    video_bitrate=self.cfg.export.video_bitrate,
                    acodec="aac",
                    audio_bitrate="192k",
                    movflags="+faststart",
                )
                seg_output = ffmpeg.overwrite_output(seg_output)
                try:
                    seg_output.run(quiet=True, capture_stdout=True, capture_stderr=True)
                except ffmpeg.Error as e:  # pragma: no cover - 依赖环境 ffmpeg
                    error_msg = f"裁剪片段失败 (idx={idx}, {item.t_start}-{item.t_end}): {e}"
                    if hasattr(e, "stderr") and e.stderr:
                        error_msg += f"\nffmpeg stderr 输出:\n{e.stderr.decode('utf-8', errors='replace')}"
                    raise RuntimeError(error_msg) from e

                segment_paths.append(seg_path)

            if not segment_paths:
                raise ValueError("EDL 为空或全部片段时长为 0，无法导出")

            # 准备 concat 列表文件
            concat_list = tmpdir_path / "concat.txt"
            concat_list.write_text(
                "\n".join(f"file '{path}'" for path in segment_paths),
                encoding="utf-8",
            )

            final_output = ffmpeg.input(str(concat_list), format="concat", safe=0)
            out = ffmpeg.output(
                final_output,
                str(output_path),
                c="copy",
                movflags="+faststart",
            )
            out = ffmpeg.overwrite_output(out)

            try:
                out.run(quiet=True, capture_stdout=True, capture_stderr=True)
            except ffmpeg.Error as e:  # pragma: no cover
                error_msg = f"ffmpeg 拼接失败: {e}"
                if hasattr(e, "stderr") and e.stderr:
                    error_msg += f"\nffmpeg stderr 输出:\n{e.stderr.decode('utf-8', errors='replace')}"
                raise RuntimeError(error_msg) from e
