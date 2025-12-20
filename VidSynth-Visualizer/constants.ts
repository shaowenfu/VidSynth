
import { VideoResource, ClusterPoint, LogEntry, Segment } from './types';

// Helper to generate segments
const generateSegments = (idPrefix: string, count: number, maxDuration: number): Segment[] => {
  const segments: Segment[] = [];
  let lastEnd = 0;
  for (let i = 0; i < count; i++) {
    // Tighter gaps for a "busy" timeline look
    const gap = Math.random() < 0.3 ? 0 : Math.random() * 0.5; 
    const start = Math.min(lastEnd + gap, maxDuration - 0.5);
    // Varied duration 1.5s - 3.5s
    const duration = 1.5 + Math.random() * 2; 
    const end = Math.min(start + duration, maxDuration);
    
    if (start >= maxDuration) break;

    const baseScore = 0.6 + Math.random() * 0.39;
    
    segments.push({
      id: `${idPrefix}_${String(i + 1).padStart(2, '0')}`,
      start: parseFloat(start.toFixed(2)),
      end: parseFloat(end.toFixed(2)),
      label: `Clip ${i + 1}`,
      score: parseFloat(baseScore.toFixed(2)),
      posScore: parseFloat((baseScore * (0.8 + Math.random() * 0.2)).toFixed(2)),
      negScore: parseFloat(((1 - baseScore) * (0.5 + Math.random() * 0.5)).toFixed(2)),
    });
    lastEnd = end;
  }
  return segments;
};

export const MOCK_VIDEOS: VideoResource[] = Array.from({ length: 7 }).map((_, i) => {
  const id = `v${i + 1}`;
  const duration = 20;
  
  return {
    id,
    name: `video_source_${(i + 1).toString().padStart(2, '0')}.mp4`,
    url: [
      'https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
      'https://storage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
      'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
      'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
      'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
      'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4',
      'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4'
    ][i % 7],
    thumbnail: `https://picsum.photos/300/170?random=${i + 200}`,
    duration: duration,
    hasGT: true, 
    status: i === 0 ? 'done' : 'idle',
    groundTruth: {
      segments: generateSegments(`gt_${id}`, 6 + Math.floor(Math.random() * 3), duration)
    },
    // Populate predicted segments for all videos to support Semantic Radar visualization
    predictedSegments: generateSegments(`pred_${id}`, 5 + Math.floor(Math.random() * 4), duration)
  };
});

export const MOCK_LOGS: LogEntry[] = [
  { id: 'l1', type: 'info', message: 'Pipeline initialized for batch (7 files)', timestamp: '10:00:01' },
  { id: 'l2', type: 'filter', message: 'Dropped segment #04 (Score 0.15 < Threshold 0.2)', timestamp: '10:00:05' },
  { id: 'l3', type: 'merge', message: 'Combined segment #07 and #08 (Gap 0.1s < 0.5s)', timestamp: '10:00:06' },
  { id: 'l4', type: 'result', message: 'Segmentation complete: 8 clips identified.', timestamp: '10:00:08' },
];

export const generateClusterPoints = (count: number): ClusterPoint[] => {
  const points: ClusterPoint[] = [];
  for (let i = 0; i < count; i++) {
    const clusterId = Math.floor(Math.random() * 4);
    let xBase = 0, yBase = 0;
    if (clusterId === 0) { xBase = 10; yBase = 10; } // Top Left
    if (clusterId === 1) { xBase = 70; yBase = 80; } // Bottom Right
    if (clusterId === 2) { xBase = 80; yBase = 20; } // Top Right
    if (clusterId === 3) { xBase = 20; yBase = 70; } // Bottom Left
    
    points.push({
      id: `c-${i}`,
      x: xBase + Math.random() * 15,
      y: yBase + Math.random() * 15,
      clusterId,
      thumbnail: `https://picsum.photos/100/100?random=${i + 500}`
    });
  }
  return points;
};

export const SAMPLE_POSITIVE_TAGS = ["extreme sports", "snowboarding", "jump", "slomo"];
export const SAMPLE_NEGATIVE_TAGS = ["static shot", "audience", "logo", "blurred"];
