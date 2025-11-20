"""VidSynth Typer CLI，便于在命令行触发各阶段流程。"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List, Optional, Sequence

import typer

from vidsynth.core import Clip, PipelineConfig, ThemeScore, load_config, setup_logging
from vidsynth.segment import segment_video
from vidsynth.segment.clipper import SegmentResult
from vidsynth.segment.loader import VideoOpenError
from vidsynth.theme_match import ThemeMatcher, build_theme_query
from vidsynth.core.config import _load_local_env
from vidsynth.sequence import Sequencer

_load_local_env()
app = typer.Typer(help="VidSynth 开发 CLI")


@app.callback()
def main() -> None:
    """VidSynth 顶层 CLI，占位以展示子命令列表。"""

    # 未来可在此添加共享选项，如全局日志级别或配置路径
    return None


def _resolve_config(config_path: Optional[Path]) -> PipelineConfig:
    return load_config(config_path) if config_path else load_config()


def _apply_embedding_overrides(cfg: PipelineConfig, *, backend: Optional[str], preset: Optional[str], device: Optional[str]) -> PipelineConfig:
    if not any([backend, preset, device]):
        return cfg
    embedding = cfg.embedding.model_copy()
    updates = {}
    if backend:
        updates["backend"] = backend
    if preset:
        updates["preset"] = preset
    if device:
        updates["device"] = device
    new_embedding = embedding.model_copy(update=updates)
    return cfg.model_copy(update={"embedding": new_embedding})


def _load_clips_from_file(path: Path) -> List[Clip]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Clip JSON 需为数组格式")
    return [Clip.from_dict(entry) for entry in payload]


def _dump_scores_json(scores: Sequence[ThemeScore], path: Path) -> None:
    data = [score.to_dict() for score in scores]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _dump_scores_csv(scores: Sequence[ThemeScore], path: Path) -> None:
    fieldnames = ["clip_id", "video_id", "theme", "score", "s_pos", "s_neg", "emb_model", "created_at", "metadata"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for score in scores:
            payload = score.to_dict()
            payload["metadata"] = json.dumps(payload.get("metadata", {}), ensure_ascii=False)
            writer.writerow(payload)


@app.command("segment-video")
def segment_video_cmd(
    video: Path = typer.Argument(Path("assets/raw/ComparingSnowGoggles.mp4"), exists=True, resolve_path=True, help="待切分视频路径"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Clip JSON 输出路径"),
    video_id: Optional[str] = typer.Option("vedeo_test", "--video-id", help="视频 ID，默认取文件名"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="自定义配置文件"),
    embedding_backend: Optional[str] = typer.Option(None, "--embedding-backend", help="覆盖 embedding backend，如 mean_color/open_clip"),
    embedding_preset: Optional[str] = typer.Option(None, "--embedding-preset", help="OpenCLIP 预设：cpu-small/gpu-large"),
    embedding_device: Optional[str] = typer.Option(None, "--embedding-device", help="指定设备，如 cpu/cuda"),
    log_level: str = typer.Option("INFO", "--log-level", help="日志级别"),
) -> None:
    """切分单个视频并导出 JSON 片段清单。"""

    setup_logging(log_level)
    cfg = _resolve_config(config_path)
    cfg = _apply_embedding_overrides(
        cfg,
        backend=embedding_backend,
        preset=embedding_preset,
        device=embedding_device,
    )

    target_video_id = video_id or video.stem
    try:
        result: SegmentResult = segment_video(
            video_id=target_video_id,
            video_path=video,
            config=cfg,
        )
    except VideoOpenError as exc:  # pragma: no cover - 依赖外部文件
        typer.echo(f"无法打开视频：{exc}", err=True)
        raise typer.Exit(code=1) from exc

    output = output or Path(f"clips_{video.stem}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = [clip.to_dict() for clip in result.clips]
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"生成 {len(payload)} 个片段，输出到 {output}")


@app.command("match-theme")
def match_theme_cmd(
    clips: Path = typer.Argument(Path("output/clips.json"), exists=True, resolve_path=True, help="Step1 产出的 Clip JSON 路径"),
    theme: str = typer.Argument(..., help="待匹配的主题关键词"),
    output: Path = typer.Option(Path("output/theme_scores.json"), "--output", "-o", help="主题得分输出路径 (JSON/CSV)"),
    positives: Optional[List[str]] = typer.Option(None, "--positive", "-p", help="附加正向原型描述，可重复"),
    negatives: Optional[List[str]] = typer.Option(None, "--negative", "-n", help="附加负向原型描述，可重复"),
    score_threshold: Optional[float] = typer.Option(None, "--score-threshold", help="覆盖配置中的得分阈值"),
    output_format: str = typer.Option("json", "--format", help="输出格式：json 或 csv", case_sensitive=False),
    config_path: Optional[Path] = typer.Option(None, "--config", help="自定义配置文件"),
    embedding_backend: Optional[str] = typer.Option(None, "--embedding-backend", help="覆盖 embedding backend，如 open_clip"),
    embedding_preset: Optional[str] = typer.Option(None, "--embedding-preset", help="OpenCLIP 预设：cpu-small/gpu-large"),
    embedding_device: Optional[str] = typer.Option(None, "--embedding-device", help="指定设备，如 cpu/cuda"),
    log_level: str = typer.Option("INFO", "--log-level", help="日志级别"),
) -> None:
    """读取 Clip JSON 并输出主题匹配得分。"""

    setup_logging(log_level)
    cfg = _resolve_config(config_path)
    cfg = _apply_embedding_overrides(
        cfg,
        backend=embedding_backend,
        preset=embedding_preset,
        device=embedding_device,
    )

    clips_data = _load_clips_from_file(clips)
    query = build_theme_query(theme=theme, positives=positives, negatives=negatives)

    matcher = ThemeMatcher(embedding_config=cfg.embedding, match_config=cfg.theme_match)
    scores = matcher.score_clips(clips_data, query)
    threshold = score_threshold if score_threshold is not None else cfg.theme_match.score_threshold
    filtered = matcher.filter_scores(scores, threshold=threshold)

    output.parent.mkdir(parents=True, exist_ok=True)
    fmt = output_format.lower()
    if fmt == "json":
        _dump_scores_json(filtered, output)
    elif fmt == "csv":
        _dump_scores_csv(filtered, output)
    else:
        raise typer.BadParameter("--format 仅支持 json/csv", param_name="format")

    typer.echo(f"{len(filtered)} / {len(scores)} clips 达到阈值 {threshold:.3f}")
    preview = filtered[:3]
    if preview:
        typer.echo("Top clips:")
        for item in preview:
            typer.echo(f" - clip#{item.clip_id} score={item.score:.3f} pos={item.s_pos:.3f} neg={item.s_neg:.3f}")


@app.command("sequence-clips")
def sequence_clips_cmd(
    clips: Path = typer.Argument(Path("output/clips.json"), exists=True, resolve_path=True, help="Step1 产出的 Clip JSON 路径"),
    theme_scores: Path = typer.Argument(Path("output/theme_scores.json"), exists=True, resolve_path=True, help="Step2 产出的主题得分 JSON 路径"),
    output_edl: Path = typer.Option(Path("output/edl.json"), "--output", "-o", help="EDL JSON 输出路径"),
    threshold_upper: Optional[float] = typer.Option(None, "--upper", help="选择阈值上界"),
    threshold_lower: Optional[float] = typer.Option(None, "--lower", help="迟滞阈值下界"),
    min_clip_seconds: Optional[float] = typer.Option(None, "--min-seconds", help="合并后片段最短时长"),
    max_clip_seconds: Optional[float] = typer.Option(None, "--max-seconds", help="合并后片段最长时长"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="自定义配置文件（用于读取默认阈值）"),
    log_level: str = typer.Option("INFO", "--log-level", help="日志级别"),
) -> None:
    """将主题得分与 Clips 对齐，生成连续超阈值的 EDL。"""

    setup_logging(log_level)
    cfg = _resolve_config(config_path)

    clip_list = _load_clips_from_file(clips)
    scores_payload = json.loads(theme_scores.read_text(encoding="utf-8"))
    scores = [ThemeScore.from_dict(entry) for entry in scores_payload]

    upper = threshold_upper if threshold_upper is not None else cfg.theme_match.score_threshold
    lower = threshold_lower if threshold_lower is not None else upper
    seq = Sequencer(
        threshold_upper=upper,
        threshold_lower=lower,
        min_clip_seconds=min_clip_seconds if min_clip_seconds is not None else cfg.segment.min_clip_seconds,
        max_clip_seconds=max_clip_seconds if max_clip_seconds is not None else cfg.segment.max_clip_seconds,
    )
    result = seq.sequence(clip_list, scores)

    edl_data = [
        {"video_id": item.video_id, "t_start": item.t_start, "t_end": item.t_end, "reason": item.reason}
        for item in result.edl
    ]
    output_edl.parent.mkdir(parents=True, exist_ok=True)
    output_edl.write_text(json.dumps(edl_data, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"生成 EDL 段数：{len(edl_data)}，选中 clips：{result.total_selected} / {result.total_clips}")


@app.command("export-edl")
def export_edl_cmd(
    edl: Path = typer.Argument(Path("output/edl.json"), exists=True, resolve_path=True, help="EDL JSON 路径"),
    source_video: Path = typer.Argument(Path("assets/raw/ComparingSnowGoggles.mp4"), exists=True, resolve_path=True, help="源视频路径（当前 MVP 以单源简化）"),
    output: Path = typer.Option(Path("output/output_demo.mp4"), "--output", "-o", help="输出 MP4 路径"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="自定义配置文件"),
    log_level: str = typer.Option("INFO", "--log-level", help="日志级别"),
) -> None:
    """读取 EDL 并导出 MP4。当前 MVP 假设所有片段来自同一源视频。"""

    setup_logging(log_level)
    cfg = _resolve_config(config_path)
    from vidsynth.export import Exporter
    exporter = Exporter(cfg)
    items = exporter.load_edl(edl)
    output.parent.mkdir(parents=True, exist_ok=True)
    exporter.export(items, source_video=source_video, output_path=output)
    typer.echo(f"导出完成：{output}")


if __name__ == "__main__":  # pragma: no cover
    app()
