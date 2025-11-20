from __future__ import annotations

# 本模块负责：
# 1) 根据 Step2 主题得分（ThemeScore）从 Clip 列表中选择片段；
# 2) 使用上/下阈值的“迟滞”策略，减少选择抖动；
# 3) 将相同视频且 clip_id 连续的片段合并为更长段，生成 EDL（剪辑列表）。

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

from vidsynth.core import Clip, ThemeScore


@dataclass(slots=True)
class EDLItem:
    """EDL（剪辑列表）中的单个条目。

    - video_id: 源视频标识（当前 MVP 按单源处理，未来可扩展多源）。
    - t_start/t_end: 该段在源视频中的起止时间（秒）。
    - reason: 生成该段的原因或标签，便于后续可视化/审计。
    """

    video_id: str
    t_start: float
    t_end: float
    reason: str


@dataclass(slots=True)
class SequenceResult:
    """序列化结果集合。

    - selected_clips: 被选中的基础 Clip 列表（未合并）。
    - edl: 合并后的 EDL 条目列表（用于导出阶段）。
    - total_selected/total_clips: 统计信息，便于日志与评估。
    """

    selected_clips: List[Clip]
    edl: List[EDLItem]
    total_selected: int
    total_clips: int


class Sequencer:
    """片段筛选与合并策略实现。

    参数：
    - threshold_upper: 上阈值；得分达到该值时开始选择。
    - threshold_lower: 下阈值；在已选择状态下，如果得分仍高于该值则继续选择（迟滞，避免抖动）。
    - min_clip_seconds/max_clip_seconds: 合并后片段的最短/最长时长约束（在生成 EDL 时生效）。
    """

    def __init__(
        self,
        *,
        threshold_upper: float,
        threshold_lower: Optional[float] = None,
        min_clip_seconds: Optional[float] = None,
        max_clip_seconds: Optional[float] = None,
    ) -> None:
        self.threshold_upper = threshold_upper
        self.threshold_lower = threshold_lower if threshold_lower is not None else threshold_upper
        self.min_clip_seconds = min_clip_seconds
        self.max_clip_seconds = max_clip_seconds

    def sequence(
        self,
        clips: Sequence[Clip],
        scores: Sequence[ThemeScore],
    ) -> SequenceResult:
        """主流程：将主题得分与 Clip 对齐并选择，随后合并为 EDL。

        输入：
        - clips: Step1 生成的片段列表。
        - scores: Step2 生成的主题得分列表（通过 `(video_id, clip_id)` 对齐）。

        选择策略（迟滞）：
        - 若得分 >= 上阈值：进入选择状态并选中当前片段；
        - 若已在选择状态且得分 >= 下阈值：继续选中；
        - 否则：退出选择状态。
        """

        # 构建 (video_id, clip_id) → ThemeScore 的映射，避免跨视频混淆
        score_map: Dict[tuple[str, int], ThemeScore] = {(s.video_id, s.clip_id): s for s in scores}
        # 先按 (video_id, clip_id) 排序，保证选择过程与时间线一致
        ordered = sorted(list(clips), key=lambda c: (c.video_id, c.clip_id))
        selected: List[Clip] = []
        last_selected = False  # 表示当前是否处于“选择维持”状态
        for clip in ordered:
            sc = score_map.get((clip.video_id, clip.clip_id))
            s_val = sc.score if sc else float("-inf")
            if s_val >= self.threshold_upper:
                selected.append(clip)
                last_selected = True
            elif last_selected and s_val >= self.threshold_lower:
                selected.append(clip)
            else:
                last_selected = False

        # 将连续的（同视频、clip_id 连续）片段合并为 EDL 段
        edl = self._merge_to_edl(selected)
        return SequenceResult(
            selected_clips=selected,
            edl=edl,
            total_selected=len(selected),
            total_clips=len(clips),
        )

    def _merge_to_edl(self, clips: Sequence[Clip]) -> List[EDLItem]:
        """将已选中的基础片段按连续性合并为 EDL 段。

        合并规则：
        - 仅在相同 `video_id` 且 `clip_id` 连续时合并；
        - `flush` 时应用最短/最长时长约束；超过最大时长将截断；
        - 产出条目的 `reason` 固定为 `theme_sequence`（后续可扩展不同原因）。
        """

        if not clips:
            return []
        edl: List[EDLItem] = []
        group: List[Clip] = []

        def flush(cur: List[Clip]) -> None:
            # 将当前累积的连续片段合并输出为一个 EDL 条目
            if not cur:
                return
            video_id = cur[0].video_id
            t_start = cur[0].t_start
            t_end = cur[-1].t_end
            # 最短时长约束：过短段丢弃，避免碎片化
            if self.min_clip_seconds is not None and t_end - t_start < self.min_clip_seconds:
                return
            # 最长时长约束：过长段按最大时长截断
            if self.max_clip_seconds is not None and t_end - t_start > self.max_clip_seconds:
                t_end = t_start + self.max_clip_seconds
            edl.append(EDLItem(video_id=video_id, t_start=t_start, t_end=t_end, reason="theme_sequence"))

        prev_vid: Optional[str] = None
        prev_id: Optional[int] = None
        for clip in clips:
            # 连续性：同视频且 clip_id 递增 1
            contiguous = prev_vid == clip.video_id and prev_id is not None and clip.clip_id == prev_id + 1
            if group and contiguous:
                group.append(clip)
            else:
                flush(group)
                group = [clip]
            prev_vid = clip.video_id
            prev_id = clip.clip_id
        flush(group)
        return edl