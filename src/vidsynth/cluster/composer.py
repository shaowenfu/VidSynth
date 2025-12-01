"""
Cluster Video Composer: Stitches representative clips into a summary video for each cluster.
"""
from __future__ import annotations

from pathlib import Path
from typing import List
import logging

from vidsynth.core import PipelineConfig
from vidsynth.export.exporter import Exporter, EDLItemPayload
from vidsynth.cluster.engine import ClusterResult

logger = logging.getLogger(__name__)

class ClusterVideoComposer:
    def __init__(self, config: PipelineConfig):
        self.exporter = Exporter(config)

    def compose_all(self, clusters: List[ClusterResult], source_video_path: Path, output_dir: Path) -> List[Path]:
        """
        Generates a video for each cluster using its representative clips.
        
        Args:
            clusters: List of ClusterResult objects.
            source_video_path: Path to the original source video.
            output_dir: Directory to save generated videos.
            
        Returns:
            List of paths to generated videos.
        """
        generated_files = []
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for cluster in clusters:
            # Construct EDL from representative clips
            edl_items = []
            for clip in cluster.representative_clips:
                edl_items.append(EDLItemPayload(
                    video_id=clip.video_id,
                    t_start=clip.t_start,
                    t_end=clip.t_end,
                    reason=f"cluster_{cluster.cluster_id}_rep"
                ))
            
            # Sort by time if desired, or keep 'closeness to centroid' order?
            # The requirement says "Representative video". Usually keeping them time-sorted 
            # makes more sense for viewing, but "centroid order" shows the "most representative" first.
            # However, jumping back and forth in time is jarring. 
            # Let's stick to the order provided by the engine (closeness to centroid) as per "visual similarity" logic,
            # OR sort by time to make it watchable. 
            # Docs say: "拼接起来，生成一个代表该簇的视频片段".
            # Let's keep engine order (relevance) for now as it highlights the cluster center best.
            
            output_filename = f"cluster_{cluster.cluster_id:02d}_summary.mp4"
            output_path = output_dir / output_filename
            
            try:
                logger.info(f"Exporting cluster {cluster.cluster_id} video to {output_path}...")
                self.exporter.export(edl_items, source_video=source_video_path, output_path=output_path)
                generated_files.append(output_path)
            except Exception as e:
                logger.error(f"Failed to export cluster {cluster.cluster_id}: {e}")
                
        return generated_files
