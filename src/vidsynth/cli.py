"""VidSynth Typer CLI，便于在命令行触发各阶段流程。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from vidsynth.core import PipelineConfig, load_config, setup_logging
from vidsynth.segment import segment_video
from vidsynth.segment.clipper import SegmentResult
from vidsynth.segment.loader import VideoOpenError

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


@app.command("segment-video")
def segment_video_cmd(
    video: Path = typer.Argument(..., exists=True, resolve_path=True, help="待切分视频路径"),
    output: Path = typer.Option(Path("clips.json"), "--output", "-o", help="Clip JSON 输出路径"),
    video_id: Optional[str] = typer.Option(None, "--video-id", help="视频 ID，默认取文件名"),
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

    output.parent.mkdir(parents=True, exist_ok=True)
    payload = [clip.to_dict() for clip in result.clips]
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"生成 {len(payload)} 个片段，输出到 {output}")


if __name__ == "__main__":  # pragma: no cover
    app()
