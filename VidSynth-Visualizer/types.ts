export interface Segment {
  id: string;
  start: number; // seconds
  end: number; // seconds
  score?: number; // 0-1
  label?: string;
  thumbnailUrl?: string;
  posScore?: number;
  negScore?: number;
}

export interface GroundTruth {
  segments: Segment[];
}

export type TaskStatus = 'idle' | 'queued' | 'running' | 'cached' | 'done' | 'error';

export interface VideoResource {
  id: string;
  name: string;
  url: string; // Video source URL
  thumbnail: string;
  duration: number; // seconds
  hasGT: boolean;
  status: TaskStatus;
  groundTruth?: GroundTruth;
  predictedSegments: Segment[];
  segmented?: boolean;
  clipsUrl?: string | null;
  gtUrl?: string | null;
  progress?: number | null;
}

export interface ThemeDefinition {
  keywords: string[];
  positiveTags: string[];
  negativeTags: string[];
}

export interface ClusterPoint {
  id: string;
  x: number;
  y: number;
  clusterId: number;
  thumbnail: string;
}

export interface LogEntry {
  id: string;
  type: 'filter' | 'merge' | 'result' | 'info';
  message: string;
  timestamp: string;
}

export interface EdlItem {
  id: string;
  sourceId: string;
  sourceStart: number;
  sourceEnd: number;
  targetStart: number;
  targetEnd: number;
}

export interface AssetRecord {
  id: string;
  name: string;
  duration: number;
  hasGT: boolean;
  segmented: boolean;
  video_url: string;
  thumb_url?: string | null;
  gt_url?: string | null;
  clips_url?: string | null;
  status?: TaskStatus;
  progress?: number | null;
}
