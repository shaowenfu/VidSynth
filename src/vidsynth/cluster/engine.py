"""
Cluster Engine: Handles feature extraction, normalization, clustering, and representative selection.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
from sklearn.metrics import pairwise_distances_argmin_min

from vidsynth.core import Clip, get_logger

logger = get_logger(__name__)

@dataclass
class ClusterResult:
    cluster_id: int
    representative_clips: List[Clip]  # Ordered by distance to centroid (closest first)
    all_clips: List[Clip]
    center_embedding: List[float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "size": len(self.all_clips),
            "representative_clip_ids": [c.clip_id for c in self.representative_clips],
            "all_clip_ids": [c.clip_id for c in self.all_clips],
            "potential_labels": [] # Placeholder for future VLM labeling
        }

class ClusterEngine:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state

    def perform_clustering(self, clips: List[Clip], max_clusters: int = 20, representative_count: int = 5) -> List[ClusterResult]:
        """
        Performs K-Means clustering on clip embeddings.
        
        Args:
            clips: List of Clip objects.
            max_clusters: Maximum number of clusters.
            representative_count: Number of clips to select as representatives (closest to centroid).
            
        Returns:
            List of ClusterResult objects.
        """
        if not clips:
            logger.warning("No clips provided for clustering.")
            return []

        logger.info("Starting clustering. Input clips: %d, Max clusters: %d", len(clips), max_clusters)

        # 1. Prepare data
        # Extract embeddings
        embeddings = np.array([clip.vis_emb_avg for clip in clips])
        
        # L2 Normalization (Crucial for Cosine Similarity behavior with KMeans)
        # norm='l2' is default, but explicit is better.
        normalized_embeddings = normalize(embeddings, norm='l2')

        # 2. Determine K
        N = len(clips)
        # Strategy: K = min(N/5, max_clusters). If N < 5, K=1.
        k = min(int(N / 5), max_clusters)
        k = max(1, k) # Ensure at least 1 cluster

        logger.debug("Determined K=%d for clustering.", k)

        # 3. Run KMeans
        kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
        labels = kmeans.fit_predict(normalized_embeddings)
        
        # 4. Organize results
        clusters: Dict[int, List[Clip]] = {i: [] for i in range(k)}
        for idx, label in enumerate(labels):
            clusters[label].append(clips[idx])
            
        results = []
        
        for cluster_id in range(k):
            cluster_clips = clusters[cluster_id]
            if not cluster_clips:
                continue
                
            centroid = kmeans.cluster_centers_[cluster_id].reshape(1, -1)
            
            # Get embeddings for clips in this cluster
            cluster_embeddings_indices = [i for i, label in enumerate(labels) if label == cluster_id]
            cluster_embeddings = normalized_embeddings[cluster_embeddings_indices]
            
            # Calculate distances to centroid
            # sklearn pairwise_distances returns matrix, we want 1D array of distances
            from sklearn.metrics.pairwise import euclidean_distances
            dists = euclidean_distances(cluster_embeddings, centroid).flatten()
            
            # Sort indices by distance
            sorted_local_indices = dists.argsort()
            
            # Select representatives
            sorted_clips = [cluster_clips[i] for i in sorted_local_indices]
            reps = sorted_clips[:representative_count]
            
            results.append(ClusterResult(
                cluster_id=cluster_id,
                representative_clips=reps,
                all_clips=cluster_clips,
                center_embedding=kmeans.cluster_centers_[cluster_id].tolist()
            ))
            
        logger.info("Clustering finished. Generated %d clusters.", len(results))
        return results
