import json
import os
import numpy as np
from datetime import datetime
from pathlib import Path
import subprocess


def _resolve_workspace_root() -> Path:
    env_value = os.getenv("VIDSYNTH_WORKSPACE_ROOT")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "workspace"


def create_dummy_data():
    # 1. Create Dummy JSON
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create 10 dummy clips
    clips = []
    for i in range(10):
        clip = {
            "video_id": "video_01",
            "clip_id": i,
            "t_start": float(i),
            "t_end": float(i + 1.0),
            "fps_keyframe": 1.0,
            "vis_emb_avg": np.random.rand(512).tolist(), # Random embedding
            "emb_model": "test_model",
            "created_at": datetime.now().isoformat(),
            "version": 1
        }
        clips.append(clip)
        
    with open("output/clips.json", "w") as f:
        json.dump(clips, f)
    print("Created output/clips.json")

    # 2. Create Dummy Video
    workspace_root = _resolve_workspace_root()
    videos_dir = workspace_root / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    video_path = videos_dir / "video_01.mp4"
    
    # Generate 10s test video using ffmpeg
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=15:size=1280x720:rate=30", 
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=15", 
        "-c:v", "libx264", "-c:a", "aac", str(video_path)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Created {video_path}")


if __name__ == "__main__":
    create_dummy_data()
