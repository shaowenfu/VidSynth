#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _which_ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def _get_video_meta(video_path: Path) -> tuple[int, int, float]:
    try:
        import cv2  # type: ignore

        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
            cap.release()
            if fps <= 0:
                fps = 30.0
            return w, h, fps
    except Exception:
        pass

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        p = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,r_frame_rate",
                "-of",
                "default=noprint_wrappers=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
        )
        lines = [l for l in p.stdout.strip().splitlines() if l]
        vals: dict[str, str] = {}
        for line in lines:
            if "=" in line:
                k, v = line.split("=", 1)
                vals[k] = v
        w = int(vals.get("width", "1280"))
        h = int(vals.get("height", "720"))
        rate = vals.get("r_frame_rate", "30/1")
        try:
            num, den = rate.split("/")
            fps = float(num) / float(den) if float(den) != 0 else float(num)
        except Exception:
            fps = 30.0
        return w, h, fps
    return 1280, 720, 30.0


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="assets/raw/ComparingSnowGoggles.mp4")
    ap.add_argument("--clips", default="output/clips.json")
    ap.add_argument("--output-dir", default="assets/step1_results")
    ap.add_argument("--black-duration", type=float, default=1.0)
    args = ap.parse_args()

    ff = _which_ffmpeg()
    if not ff:
        print("ffmpeg not found", file=sys.stderr)
        sys.exit(1)

    video = Path(args.video).resolve()
    clips_json = Path(args.clips).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not video.exists() or not clips_json.exists():
        print("input paths not found", file=sys.stderr)
        sys.exit(1)

    with clips_json.open("r", encoding="utf-8") as f:
        data = json.load(f)
    segments = [(float(x["t_start"]), float(x["t_end"])) for x in data]
    segments.sort(key=lambda t: t[0])
    if not segments:
        print("no clips", file=sys.stderr)
        sys.exit(1)

    w, h, fps = _get_video_meta(video)
    fps_int = int(round(fps))
    tmp_dir = out_dir / f"tmp_{video.stem}"
    clips_dir = tmp_dir / "clips"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    black = tmp_dir / "black.mp4"
    _run(
        [
            ff,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s={w}x{h}:d={args.black_duration}:r={fps_int}",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps_int),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "44100",
            str(black),
        ]
    )

    concat_list = tmp_dir / "concat.txt"
    with concat_list.open("w", encoding="utf-8") as fw:
        for i, (start, end) in enumerate(segments):
            clip_path = clips_dir / f"clip_{i:04d}.mp4"
            _run(
                [
                    ff,
                    "-y",
                    "-ss",
                    str(start),
                    "-to",
                    str(end),
                    "-i",
                    str(video),
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-r",
                    str(fps_int),
                    "-vf",
                    f"scale={w}:{h}",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    "-ar",
                    "44100",
                    str(clip_path),
                ]
            )
            fw.write(f"file '{clip_path.as_posix()}'\n")
            if i != len(segments) - 1:
                fw.write(f"file '{black.as_posix()}'\n")

    out_file = out_dir / f"{video.stem}_step1_preview_with_black.mp4"
    _run(
        [
            ff,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps_int),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "44100",
            str(out_file),
        ]
    )
    print(str(out_file))


if __name__ == "__main__":
    main()