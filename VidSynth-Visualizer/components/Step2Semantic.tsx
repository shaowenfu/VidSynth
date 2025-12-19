
import React, { useState, useMemo, useRef } from 'react';
import { VideoResource, Segment } from '../types';
import { Flame, PlayCircle, Activity, Play, CheckCircle2, ScanSearch } from 'lucide-react';

interface Step2Props {
  videos: VideoResource[];
}

interface FlattenedSegment extends Segment {
  videoId: string;
  videoName: string;
  globalIndex: number;
}

const Step2Semantic: React.FC<Step2Props> = ({ videos }) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null);
  const [hoveredSegment, setHoveredSegment] = useState<{ seg: FlattenedSegment, x: number, y: number } | null>(null);
  
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Flatten all segments from all videos into a single timeline
  const allSegments = useMemo(() => {
    let index = 0;
    const flat: FlattenedSegment[] = [];
    videos.forEach(v => {
      v.predictedSegments.forEach(s => {
        flat.push({
          ...s,
          videoId: v.id,
          videoName: v.name,
          globalIndex: index++
        });
      });
    });
    return flat;
  }, [videos]);

  const handleStartAnalysis = () => {
    if (isAnalyzing) return;
    setIsAnalyzing(true);
    setProgress(0);

    // Simulate progress
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsAnalyzing(false);
          return 100;
        }
        return prev + 2;
      });
    }, 50);
  };

  const handleSegmentClick = (seg: FlattenedSegment) => {
    setSelectedSegmentId(seg.id);
    const element = itemRefs.current.get(seg.id);
    if (element && scrollContainerRef.current) {
      element.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    }
  };

  const getColorForScore = (score: number = 0) => {
     // Heatmap gradient: Blue/Grey (low) -> Purple -> Orange -> Red (high)
     if (score < 0.4) return 'bg-slate-700';
     if (score < 0.6) return 'bg-indigo-600';
     if (score < 0.8) return 'bg-orange-500';
     return 'bg-red-500';
  };

  return (
    <section className="mb-8 border-b border-slate-800 pb-8 relative snap-start scroll-mt-6">
      <div className="flex items-center justify-between mb-4 px-6">
        <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-sm">02</div>
            <h2 className="text-xl font-bold text-slate-100">Semantic Radar</h2>
            <span className="text-xs text-slate-500 uppercase tracking-wide border border-slate-700 px-2 py-0.5 rounded">Global Embedding Match</span>
        </div>
        
        {/* Analysis Controls */}
        <div className="flex items-center gap-4 bg-slate-900 border border-slate-800 p-2 rounded-lg shadow-sm">
            <div className="flex flex-col min-w-[200px]">
                <div className="flex justify-between text-[10px] text-slate-400 font-bold uppercase mb-1">
                   <span>Analysis Status</span>
                   <span className={isAnalyzing ? "text-cyan-400" : "text-emerald-400"}>
                     {isAnalyzing ? `Scanning... ${progress}%` : "Ready / Idling"}
                   </span>
                </div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                   <div 
                     className={`h-full transition-all duration-100 ${isAnalyzing ? 'bg-cyan-500' : 'bg-emerald-500'}`} 
                     style={{ width: `${isAnalyzing ? progress : 100}%` }}
                   />
                </div>
            </div>
            <button 
                onClick={handleStartAnalysis}
                disabled={isAnalyzing}
                className={`
                    px-4 py-2 rounded font-bold text-sm flex items-center gap-2 transition-all shadow-lg
                    ${isAnalyzing 
                        ? 'bg-slate-800 text-slate-500 cursor-not-allowed' 
                        : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-500/20 active:scale-95'
                    }
                `}
            >
                {isAnalyzing ? <Activity size={16} className="animate-spin" /> : <Play size={16} fill="currentColor" />}
                {isAnalyzing ? 'Analyzing...' : 'Start Analysis'}
            </button>
        </div>
      </div>

      <div className="px-6 flex flex-col gap-6">

        {/* 1. Global Relevance Heatmap (All Segments) */}
        <div className="bg-slate-900 rounded-lg p-5 border border-slate-800 shadow-inner">
           <div className="flex justify-between items-center mb-3">
             <div className="flex items-center gap-2">
                <Flame size={16} className="text-orange-500" />
                <span className="text-sm font-semibold text-slate-300">Global Timeline Heatmap</span>
                <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded text-slate-500 font-mono">{allSegments.length} clips</span>
             </div>
             <div className="flex items-center gap-2 text-[10px] text-slate-500">
               <span>Relevance</span>
               <div className="flex gap-0.5">
                   <div className="w-4 h-2 bg-slate-700 rounded-sm"></div>
                   <div className="w-4 h-2 bg-indigo-600 rounded-sm"></div>
                   <div className="w-4 h-2 bg-orange-500 rounded-sm"></div>
                   <div className="w-4 h-2 bg-red-500 rounded-sm"></div>
               </div>
             </div>
           </div>
           
           <div 
             className="relative h-12 w-full rounded bg-slate-950 border border-slate-800/50 flex overflow-hidden cursor-crosshair"
             onMouseLeave={() => setHoveredSegment(null)}
           >
              {allSegments.map((seg) => (
                   <div 
                     key={`heat-${seg.id}`}
                     onClick={() => handleSegmentClick(seg)}
                     onMouseMove={(e) => setHoveredSegment({ seg, x: e.clientX, y: e.clientY })}
                     className={`flex-1 h-full border-r border-slate-900/40 hover:brightness-125 transition-all relative group
                        ${getColorForScore(seg.score)}
                        ${selectedSegmentId === seg.id ? 'ring-2 ring-white z-10' : 'opacity-90'}
                     `}
                   >
                     {/* Active Indicator on Heatmap */}
                     {selectedSegmentId === seg.id && (
                        <div className="absolute inset-x-0 -bottom-1 h-1 bg-white shadow-[0_0_10px_white]"></div>
                     )}
                   </div>
              ))}
           </div>
           <div className="flex justify-between mt-1 text-[9px] text-slate-600 font-mono">
               <span>Start (Video 1)</span>
               <span>End (Video {videos.length})</span>
           </div>
        </div>

        {/* 2. Horizontal Clip Gallery (Fixed Height) */}
        <div>
            <div className="flex items-center gap-2 mb-3 text-slate-400 text-sm font-semibold">
                <ScanSearch size={14} />
                <span>Segment Inspection</span>
            </div>
            
            <div 
                ref={scrollContainerRef}
                className="flex gap-4 overflow-x-auto pb-4 pt-1 custom-scrollbar scroll-smooth min-h-[180px]"
            >
                {allSegments.map((seg, idx) => (
                    <div 
                        key={seg.id}
                        ref={(el) => {
                            if (el) itemRefs.current.set(seg.id, el);
                            else itemRefs.current.delete(seg.id);
                        }}
                        onClick={() => setSelectedSegmentId(seg.id)}
                        className={`
                            relative flex-shrink-0 w-48 h-36 bg-black rounded-lg border cursor-pointer transition-all duration-300 group overflow-hidden
                            ${selectedSegmentId === seg.id 
                                ? 'border-cyan-400 ring-4 ring-cyan-500/20 scale-105 z-10' 
                                : 'border-slate-800 hover:border-slate-600 hover:scale-[1.02]'
                            }
                        `}
                    >
                        {/* Thumbnail */}
                        <div className="w-full h-full opacity-60 group-hover:opacity-100 transition-opacity">
                             {/* Use a fixed seed logic for consistent thumbnail per clip id */}
                            <img 
                                src={`https://picsum.photos/300/200?random=${parseInt(seg.id.replace(/\D/g, '')) + 100}`} 
                                alt={seg.label} 
                                className="w-full h-full object-cover" 
                            />
                        </div>

                        {/* Overlay Content */}
                        <div className="absolute inset-0 flex flex-col justify-between p-3 bg-gradient-to-t from-black via-transparent to-black/40">
                            
                            {/* Top: ID */}
                            <div className="flex justify-between items-start">
                                <span className="text-[10px] font-mono text-white/70 bg-black/50 px-1.5 py-0.5 rounded backdrop-blur-md">
                                    #{idx + 1}
                                </span>
                                {selectedSegmentId === seg.id && (
                                    <CheckCircle2 size={16} className="text-cyan-400 bg-black rounded-full" />
                                )}
                            </div>
                            
                            {/* Center: Play Icon (Hover) */}
                            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                                <PlayCircle size={32} className="text-white drop-shadow-lg scale-90 group-hover:scale-100 transition-transform" />
                            </div>

                            {/* Bottom: Label & Score */}
                            <div className="text-center">
                                <h3 className="text-white font-bold text-sm drop-shadow-md mb-1">{seg.label || `Clip ${idx + 1}`}</h3>
                                <div className="inline-block bg-black/80 backdrop-blur border border-white/10 rounded px-2 py-0.5">
                                    <span className="text-[11px] font-bold text-cyan-400">Score: {(seg.score || 0).toFixed(2)}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>

      </div>

      {/* 3. Light Theme Tooltip (Hover on Heatmap) */}
      {hoveredSegment && (
        <div 
            className="fixed z-[100] bg-white/95 backdrop-blur text-slate-900 p-3 rounded-lg shadow-[0_10px_30px_rgba(0,0,0,0.5)] pointer-events-none flex flex-col gap-1 min-w-[140px] animate-in fade-in zoom-in-95 duration-100 border border-slate-200"
            style={{ 
                left: hoveredSegment.x, 
                top: hoveredSegment.y - 120,
                transform: 'translateX(-50%)' 
            }}
        >
            <div className="border-b border-slate-200 pb-1 mb-1 flex justify-between items-center">
                <span className="font-bold text-xs">Clip {hoveredSegment.seg.label?.split(' ')[1] || hoveredSegment.seg.id}</span>
                <span className="text-[9px] text-slate-500">{hoveredSegment.seg.videoName}</span>
            </div>
            
            <div className="space-y-1">
                <div className="flex justify-between text-[10px]">
                    <span className="text-emerald-600 font-bold uppercase">Pos Score</span>
                    <span className="font-mono font-bold">{(hoveredSegment.seg.posScore || 0).toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-[10px]">
                    <span className="text-rose-600 font-bold uppercase">Neg Score</span>
                    <span className="font-mono font-bold">{(hoveredSegment.seg.negScore || 0).toFixed(2)}</span>
                </div>
                <div className="h-px bg-slate-200 my-1"></div>
                <div className="flex justify-between text-xs">
                    <span className="font-bold uppercase text-slate-500">Total</span>
                    <span className="font-mono font-black text-indigo-600">{(hoveredSegment.seg.score || 0).toFixed(2)}</span>
                </div>
            </div>

            {/* Down Arrow */}
            <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-white rotate-45 border-b border-r border-slate-200"></div>
        </div>
      )}

    </section>
  );
};

export default Step2Semantic;
