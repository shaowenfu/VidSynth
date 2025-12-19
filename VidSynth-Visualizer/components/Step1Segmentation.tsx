
import React, { useCallback, useEffect, useState } from 'react';
import { VideoResource, Segment } from '../types';
import { Play, Pause, Scissors, Code, ChevronDown, MonitorPlay, Activity, FileCode, BarChart3, PieChart, TrendingUp } from 'lucide-react';

interface Step1Props {
  video: VideoResource;
  allVideos: VideoResource[];
  onSelectVideo: (id: string) => void;
}

const Step1Segmentation: React.FC<Step1Props> = ({ video, allVideos, onSelectVideo }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [hoverInfo, setHoverInfo] = useState<{ segment: Segment, x: number, y: number } | null>(null);
  
  const [predictedSegments, setPredictedSegments] = useState<Segment[]>([]);
  const [progressByVideo, setProgressByVideo] = useState<Record<string, number>>({});
  const [statusByVideo, setStatusByVideo] = useState<Record<string, 'idle' | 'pending' | 'processing' | 'done' | 'error'>>({});
  const [taskError, setTaskError] = useState<string | null>(null);

  const resolveStatus = (target: VideoResource) => {
    const stored = statusByVideo[target.id];
    if (stored) {
      return stored;
    }
    if (target.status === 'processing' || target.status === 'pending') {
      return 'processing';
    }
    if (target.status === 'ready' || target.segmented) {
      return 'done';
    }
    if (target.status === 'error') {
      return 'error';
    }
    return 'idle';
  };

  const fetchSegments = useCallback(async (videoId: string, clipsUrl?: string | null) => {
    const url = clipsUrl || `/static/segmentation/${videoId}/clips.json`;
    try {
      const response = await fetch(url);
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      if (!Array.isArray(payload)) {
        return;
      }
      const segments: Segment[] = payload.map((clip) => ({
        id: `clip_${clip.clip_id ?? clip.clipId ?? clip.id ?? ''}`,
        start: Number(clip.t_start ?? clip.start ?? 0),
        end: Number(clip.t_end ?? clip.end ?? 0),
        label: `Clip ${clip.clip_id ?? clip.clipId ?? ''}`,
      }));
      setPredictedSegments(segments);
    } catch (error) {
      return;
    }
  }, []);

  useEffect(() => {
    setPredictedSegments([]);
    setTaskError(null);
    const status = resolveStatus(video);
    if (status === 'done' || video.segmented) {
      fetchSegments(video.id, video.clipsUrl);
    }
  }, [video.id, video.segmented, video.clipsUrl, fetchSegments]);

  useEffect(() => {
    const source = new EventSource('/api/events');
    const handleMessage = (event: MessageEvent) => {
      if (!event.data) return;
      try {
        const message = JSON.parse(event.data);
        const { type, payload } = message || {};
        if (type === 'snapshot' && payload?.statuses) {
          setStatusByVideo((prev) => {
            const next = { ...prev };
            Object.entries(payload.statuses).forEach(([videoId, status]) => {
              if (status && typeof status === 'object') {
                const state = (status as any).status as 'idle' | 'pending' | 'processing' | 'done' | 'error';
                if (state) {
                  next[videoId] = state;
                }
              }
            });
            return next;
          });
          setProgressByVideo((prev) => {
            const next = { ...prev };
            Object.entries(payload.statuses).forEach(([videoId, status]) => {
              const value = (status as any)?.progress;
              if (typeof value === 'number') {
                next[videoId] = value;
              }
            });
            return next;
          });
          return;
        }
        if (type === 'status_update' && payload?.video_id) {
          const status = payload.status as 'idle' | 'pending' | 'processing' | 'done' | 'error';
          if (status) {
            setStatusByVideo((prev) => ({ ...prev, [payload.video_id]: status }));
          }
          if (typeof payload.progress === 'number') {
            setProgressByVideo((prev) => ({ ...prev, [payload.video_id]: payload.progress }));
          }
          return;
        }
        if (type === 'task_complete' && payload?.video_id) {
          setStatusByVideo((prev) => ({ ...prev, [payload.video_id]: 'done' }));
          setProgressByVideo((prev) => ({ ...prev, [payload.video_id]: 100 }));
          if (payload.video_id === video.id) {
            fetchSegments(payload.video_id, payload.clips_url);
          }
          return;
        }
        if (type === 'error' && payload?.video_id) {
          setStatusByVideo((prev) => ({ ...prev, [payload.video_id]: 'error' }));
          if (payload.video_id === video.id) {
            setTaskError(payload.message || 'Task failed');
          }
        }
      } catch (error) {
        return;
      }
    };
    source.onmessage = handleMessage;
    source.onerror = () => {
      setTaskError('SSE connection lost');
    };
    return () => source.close();
  }, [video.id, fetchSegments]);

  const handleExecute = async () => {
    const currentStatus = resolveStatus(video);
    if (currentStatus === 'processing' || currentStatus === 'pending') return;
    setTaskError(null);
    setStatusByVideo((prev) => ({ ...prev, [video.id]: 'processing' }));
    setProgressByVideo((prev) => ({ ...prev, [video.id]: 0 }));
    const force = currentStatus === 'done';
    try {
      const response = await fetch('/api/segment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_ids: [video.id], force }),
      });
      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }
    } catch (error) {
      setStatusByVideo((prev) => ({ ...prev, [video.id]: 'error' }));
      setTaskError(error instanceof Error ? error.message : 'Task failed');
    }
  };

  const formatTime = (t: number) => {
    const m = Math.floor(t / 60);
    const s = Math.floor(t % 60);
    const ms = Math.floor((t % 1) * 100);
    return `${m}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
  };

  // Distinct Color Palette for timeline clips
  const PALETTE = [
    { bg: 'bg-[#FF6B6B]', border: 'border-[#EE5253]', hover: 'hover:bg-[#FF8787]' }, // Red
    { bg: 'bg-[#4ECDC4]', border: 'border-[#45B7AA]', hover: 'hover:bg-[#70D6CE]' }, // Teal
    { bg: 'bg-[#FFE66D]', border: 'border-[#FFD93D]', hover: 'hover:bg-[#FFF799]' }, // Yellow
    { bg: 'bg-[#6C5CE7]', border: 'border-[#5541E2]', hover: 'hover:bg-[#8578EA]' }, // Purple
    { bg: 'bg-[#A8E6CF]', border: 'border-[#8BD3BA]', hover: 'hover:bg-[#C2F0E0]' }, // Mint
  ];

  const getClipColor = (index: number) => PALETTE[index % PALETTE.length];
  const currentStatus = resolveStatus(video);
  const currentProgress = progressByVideo[video.id] ?? (currentStatus === 'done' ? 100 : 0);
  const isProcessing = currentStatus === 'processing' || currentStatus === 'pending';
  const isDone = currentStatus === 'done';
  const hasPredicted = predictedSegments.length > 0;
  const hasError = currentStatus === 'error';

  return (
    <section className="h-[calc(100vh-8rem)] flex flex-col snap-start scroll-mt-24 px-6 pb-2 box-border">
      {/* Header Row - Fixed Height */}
      <div className="flex-none flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-sm">01</div>
            <h2 className="text-xl font-bold text-slate-100">Segmentation Lab</h2>
            <span className="text-xs text-slate-500 uppercase tracking-wide border border-slate-700 px-2 py-0.5 rounded">Visual Grounding</span>
        </div>

        {/* Integrated Controls */}
        <div className="flex items-center gap-3">
             {/* Target Source Dropdown */}
             <div className="relative group min-w-[200px]">
                 <select 
                   value={video.id}
                   onChange={(e) => onSelectVideo(e.target.value)}
                   className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-md pl-3 pr-8 py-2 appearance-none focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all font-medium"
                 >
                   {allVideos.map(v => (
                     <option key={v.id} value={v.id}>{v.name}</option>
                   ))}
                 </select>
                 <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none group-hover:text-cyan-500 transition-colors" />
             </div>

             {/* Execute Button */}
             <div className="w-[220px]">
                 {isProcessing ? (
                     <div className="w-full bg-slate-950 rounded-md border border-slate-700 p-0.5 relative overflow-hidden h-9 flex items-center justify-center">
                         <div className="absolute inset-0 bg-cyan-900/20 w-full h-full">
                             <div className="h-full bg-cyan-500/20 transition-all duration-75" style={{ width: `${currentProgress}%` }}></div>
                         </div>
                         <span className="relative text-[10px] font-bold text-cyan-400 font-mono tracking-wider flex items-center gap-2">
                            PROCESSING {currentProgress}%
                         </span>
                     </div>
                 ) : (
                     <button 
                        onClick={handleExecute}
                        className={`w-full font-bold h-9 rounded-md shadow-lg flex items-center justify-center gap-2 transition-all active:scale-[0.98] group text-xs
                            ${isDone 
                                ? 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-600' 
                                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-900/30'
                            }
                        `}
                    >
                        <Scissors size={14} className={isDone ? "text-slate-400" : "group-hover:rotate-12 transition-transform"} />
                        <span>{isDone ? 'Re-run Segmentation' : 'Execute Segmentation'}</span>
                    </button>
                 )}
                 {taskError && (
                   <div className="mt-2 text-[10px] text-rose-400">
                     {taskError}
                   </div>
                 )}
             </div>
        </div>
      </div>

      {/* Main Content - 3 Columns (Ratio 6 : 2 : 2) with Flex-1 to fill height */}
      <div className="flex-1 flex gap-4 h-full min-h-0">
        
        {/* COLUMN 1: Player & Minimalist Timeline (60%) */}
        <div className="w-[60%] flex flex-col gap-4 h-full min-h-0">
            {/* 1.1 Video Player - Flex-1 to take available space */}
            <div className="flex-1 bg-black rounded-lg relative overflow-hidden border border-slate-800 shadow-2xl group w-full min-h-0">
                <video 
                    className="w-full h-full object-contain"
                    src={video.url} 
                    loop 
                    muted
                />
                <div className="absolute top-4 right-4 bg-black/60 backdrop-blur rounded px-2 py-1 text-[10px] text-slate-400 border border-white/10">
                   {video.name}
                </div>
                {/* Overlay Controls */}
                <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-black via-black/60 to-transparent flex items-end px-6 py-5 gap-6 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <button 
                        onClick={() => setIsPlaying(!isPlaying)}
                        className="text-white hover:text-cyan-400 transition-colors bg-white/10 hover:bg-white/20 p-3 rounded-full backdrop-blur-md border border-white/10"
                    >
                        {isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" />}
                    </button>
                    <div className="mb-3 font-mono text-2xl font-bold text-white tracking-widest drop-shadow-md flex items-baseline gap-2">
                        {formatTime(currentTime)} <span className="text-white/40 text-sm font-medium">/ {formatTime(video.duration)}</span>
                    </div>
                </div>
            </div>

            {/* 1.2 Minimalist Timeline - Fixed Height */}
            <div className="h-32 bg-[#0f0f10] rounded-xl border border-slate-800 flex flex-col relative select-none shadow-lg overflow-hidden shrink-0">
                {/* Clean Header */}
                <div className="h-8 border-b border-slate-800/50 flex items-center justify-between px-4 bg-[#141416]">
                   <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Temporal Alignment</span>
                   <span className="text-[10px] font-mono text-slate-600">DURATION: {video.duration}s</span>
                </div>

                {/* Simple Tracks Container */}
                <div className="flex-1 px-3 flex flex-col justify-center gap-3 relative">
                    {/* Playhead Line */}
                    <div className="absolute top-0 bottom-0 z-30 pointer-events-none border-l-2 border-white/40" style={{ left: '35%' }}></div>

                    {/* Track 1: GT (Ground Truth) */}
                    <div className="h-6 flex items-center gap-3">
                        <div className="w-12 flex items-center justify-end gap-2 text-emerald-500/80">
                            <span className="text-[9px] font-bold tracking-wider">GT</span>
                            <MonitorPlay size={10} />
                        </div>
                        <div className="flex-1 h-5 bg-[#18181b] rounded relative overflow-hidden ring-1 ring-white/5">
                             {/* Background Grid */}
                             <div className="absolute inset-0 w-full h-full opacity-5" style={{ backgroundImage: 'linear-gradient(90deg, #fff 1px, transparent 1px)', backgroundSize: `${100/video.duration}% 100%` }}></div>
                             
                             {video.groundTruth?.segments.map((seg, idx) => {
                                const colors = getClipColor(idx + 2);
                                return (
                                    <div
                                        key={seg.id}
                                        onMouseEnter={(e) => setHoverInfo({ segment: seg, x: e.clientX, y: e.clientY })}
                                        onMouseMove={(e) => setHoverInfo(prev => prev ? { ...prev, x: e.clientX, y: e.clientY } : null)}
                                        onMouseLeave={() => setHoverInfo(null)}
                                        className={`absolute top-0.5 bottom-0.5 rounded-sm border-l-2 cursor-pointer transition-all ${colors.bg} ${colors.border} opacity-80 hover:opacity-100 hover:brightness-110`}
                                        style={{
                                            left: `${(seg.start / video.duration) * 100}%`,
                                            width: `${((seg.end - seg.start) / video.duration) * 100}%`,
                                        }}
                                    />
                                );
                            })}
                        </div>
                    </div>

                    {/* Track 2: Prediction (System Output) */}
                    <div className="h-6 flex items-center gap-3">
                        <div className="w-12 flex items-center justify-end gap-2 text-blue-500/80">
                             <span className="text-[9px] font-bold tracking-wider">PRED</span>
                             <Activity size={10} />
                        </div>
                        <div className="flex-1 h-5 bg-[#18181b] rounded relative overflow-hidden ring-1 ring-white/5 transition-colors">
                            {/* Empty State / Running State */}
                            {!isProcessing && !hasPredicted && !hasError && (
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <span className="text-[8px] text-slate-700 font-mono tracking-tight">-- NO SEGMENTS --</span>
                                </div>
                            )}
                            {hasError && (
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <span className="text-[8px] text-rose-400 font-mono tracking-tight">-- SEGMENTATION FAILED --</span>
                                </div>
                            )}
                            {isProcessing && (
                                <div className="absolute inset-0 bg-blue-500/10 flex items-center justify-center">
                                    <div className="w-1/3 h-0.5 bg-blue-500/30 rounded-full overflow-hidden">
                                        <div className="h-full bg-blue-400 animate-progress-indeterminate"></div>
                                    </div>
                                </div>
                            )}

                            {/* Segments (Only show when done) */}
                            {hasPredicted && predictedSegments.map((seg, idx) => {
                                const colors = getClipColor(idx);
                                return (
                                    <div
                                        key={seg.id}
                                        onMouseEnter={(e) => setHoverInfo({ segment: seg, x: e.clientX, y: e.clientY })}
                                        onMouseMove={(e) => setHoverInfo(prev => prev ? { ...prev, x: e.clientX, y: e.clientY } : null)}
                                        onMouseLeave={() => setHoverInfo(null)}
                                        className={`absolute top-0.5 bottom-0.5 rounded-sm border-l-2 cursor-pointer transition-all ${colors.bg} ${colors.border} opacity-90 hover:opacity-100 hover:scale-[1.01] shadow-sm`}
                                        style={{
                                            left: `${(seg.start / video.duration) * 100}%`,
                                            width: `${((seg.end - seg.start) / video.duration) * 100}%`,
                                        }}
                                    />
                                );
                            })}
                        </div>
                    </div>

                </div>
            </div>
        </div>

        {/* COLUMN 2: JSON Viewer (20%) */}
        <div className="w-[20%] min-w-[200px] bg-[#0f1115] rounded-lg border border-slate-800 flex flex-col overflow-hidden shadow-lg h-full">
           <div className="bg-slate-900/80 p-3 border-b border-slate-800 flex items-center justify-between backdrop-blur shrink-0">
              <div className="flex items-center gap-2">
                 <FileCode size={14} className="text-amber-500" />
                 <span className="text-xs font-bold text-slate-300 truncate">ground_truth.json</span>
              </div>
              <div className="text-[9px] text-slate-500 font-mono">ID: {video.id}</div>
           </div>
           <div className="flex-1 overflow-y-auto p-3 custom-scrollbar bg-[#09090b]">
             {video.hasGT ? (
               <pre className="text-[9px] font-mono text-emerald-400/90 leading-relaxed whitespace-pre-wrap font-medium break-all">
                 {JSON.stringify(video.groundTruth, null, 2)}
               </pre>
             ) : (
               <div className="h-full flex flex-col items-center justify-center text-slate-700 gap-3">
                 <Code size={24} strokeWidth={1.5} />
                 <span className="text-[10px] text-center px-4 leading-tight">No Ground Truth JSON mapped.</span>
               </div>
             )}
           </div>
        </div>

        {/* COLUMN 3: Segment Analysis (20%) */}
        <div className="w-[20%] min-w-[200px] bg-[#0f1115] rounded-lg border border-slate-800 flex flex-col overflow-hidden shadow-lg h-full">
           <div className="bg-slate-900/80 p-3 border-b border-slate-800 flex items-center justify-between backdrop-blur shrink-0">
              <div className="flex items-center gap-2">
                 <BarChart3 size={14} className="text-purple-500" />
                 <span className="text-xs font-bold text-slate-300 truncate">Segment Analysis</span>
              </div>
           </div>
           
           <div className="flex-1 overflow-y-auto p-4 custom-scrollbar bg-[#09090b] flex flex-col gap-6">
               {/* Analysis Widget 1 */}
               <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-800/50">
                  <div className="flex items-center gap-2 mb-3 text-slate-400">
                      <PieChart size={14} />
                      <span className="text-[10px] font-bold uppercase">Classification Split</span>
                  </div>
                  <div className="flex items-center justify-center relative w-24 h-24 mx-auto my-2">
                      <svg viewBox="0 0 36 36" className="w-full h-full rotate-[-90deg]">
                          {/* Ring Background */}
                          <path className="text-slate-800" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" />
                          {/* Segment Ring */}
                          <path className="text-purple-500" strokeDasharray="75, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center flex-col">
                          <span className="text-lg font-bold text-slate-200">75%</span>
                          <span className="text-[8px] text-slate-500">ACCURACY</span>
                      </div>
                  </div>
               </div>

               {/* Analysis Widget 2 */}
               <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-800/50 flex-1">
                   <div className="flex items-center gap-2 mb-3 text-slate-400">
                      <TrendingUp size={14} />
                      <span className="text-[10px] font-bold uppercase">Trend Variance</span>
                  </div>
                  <div className="h-32 flex items-end justify-between gap-1 px-1">
                      {[40, 65, 35, 80, 50, 70, 45].map((h, i) => (
                          <div key={i} className="w-full bg-slate-800 rounded-sm hover:bg-purple-500 transition-colors relative group">
                              <div className="absolute bottom-0 left-0 right-0 bg-purple-600/20 rounded-sm" style={{ height: `${h}%` }}>
                                  <div className="absolute top-0 left-0 right-0 h-0.5 bg-purple-500/50"></div>
                              </div>
                          </div>
                      ))}
                  </div>
               </div>
           </div>
        </div>

      </div>

      {/* Hover Tooltip */}
      {hoverInfo && (
        <div 
            className="fixed z-[100] bg-white text-slate-900 p-2 rounded shadow-xl pointer-events-none flex flex-col gap-0.5 min-w-[120px] border border-slate-200"
            style={{ left: hoverInfo.x, top: hoverInfo.y - 80, transform: 'translateX(-50%)' }}
        >
            <div className="flex justify-between items-center text-[10px] font-bold border-b border-slate-100 pb-1 mb-1">
                <span>{hoverInfo.segment.label || hoverInfo.segment.id}</span>
                <span className="bg-slate-100 px-1 rounded text-slate-500">{hoverInfo.segment.score?.toFixed(2) || 'GT'}</span>
            </div>
            <div className="text-[10px] text-slate-500 font-mono">
                {hoverInfo.segment.start.toFixed(2)}s - {hoverInfo.segment.end.toFixed(2)}s
            </div>
            <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-white rotate-45"></div>
        </div>
      )}
    </section>
  );
};

export default Step1Segmentation;
