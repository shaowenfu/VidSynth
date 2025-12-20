
import React from 'react';
import { Upload, FileJson, CheckCircle, FileText, Plus, Database } from 'lucide-react';
import { VideoResource } from '../types';

interface TopBarProps {
  videos: VideoResource[];
  activeVideoId: string;
  onSelectVideo: (id: string) => void;
  onUploadGT: () => void;
}

const TopBar: React.FC<TopBarProps> = ({ videos, activeVideoId, onSelectVideo, onUploadGT }) => {
  return (
    <div className="sticky top-0 z-50 bg-slate-900/95 backdrop-blur-sm border-b border-slate-700 shadow-xl">
      <div className="flex h-48"> 
        
        {/* Left: Video Pool (Expanded) */}
        <div className="flex-[3] border-r border-slate-700 p-4 flex flex-col gap-2 min-w-0">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
              Video Resource Pool ({videos.length})
            </span>
            <button className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300 bg-cyan-950/30 px-3 py-1.5 rounded transition-colors border border-cyan-900/50">
              <Upload size={12} /> Add Sources
            </button>
          </div>
          
          <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-hide h-full items-center">
            {videos.map((vid) => (
              <div
                key={vid.id}
                onClick={() => onSelectVideo(vid.id)}
                className={`relative group flex-shrink-0 w-56 h-32 cursor-pointer transition-all ${
                  activeVideoId === vid.id 
                    ? 'ring-2 ring-cyan-500 rounded-lg scale-105 z-10 shadow-xl shadow-cyan-900/20' 
                    : 'opacity-70 hover:opacity-100 hover:scale-105'
                }`}
              >
                <div className="w-full h-full bg-slate-800 rounded-lg overflow-hidden relative shadow-md">
                   <img src={vid.thumbnail} alt={vid.name} className="w-full h-full object-cover" />
                   <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/10 to-transparent" />
                   
                   {/* Info Badge */}
                   <div className="absolute bottom-2 left-2 right-2">
                      <div className="text-[11px] text-white font-medium truncate drop-shadow-md">{vid.name}</div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-slate-300 bg-black/40 px-1.5 rounded backdrop-blur-sm font-mono">{vid.duration}s</span>
                      </div>
                   </div>
                   
                   {/* Status Indicator */}
                   <div className="absolute top-2 right-2">
                     {(vid.status === 'done' || vid.status === 'cached') && (
                       <CheckCircle size={16} className="text-emerald-400 bg-black/50 rounded-full" />
                     )}
                     {(vid.status === 'running' || vid.status === 'queued') && (
                       <div className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse box-content border-2 border-black/50" />
                     )}
                   </div>
                   
                   {/* Selection Ring */}
                   {activeVideoId === vid.id && (
                     <div className="absolute inset-0 border-2 border-cyan-500 rounded-lg pointer-events-none" />
                   )}
                </div>
              </div>
            ))}
            
            {/* Add placeholder */}
            <div className="flex-shrink-0 w-56 h-32 border-2 border-dashed border-slate-700/50 rounded-lg flex flex-col items-center justify-center gap-3 cursor-pointer hover:border-slate-500 hover:bg-slate-800/30 transition-colors group">
                <div className="p-3 bg-slate-800 rounded-full group-hover:bg-slate-700 transition-colors">
                    <Plus className="text-slate-500 group-hover:text-slate-300" />
                </div>
                <span className="text-xs text-slate-600 group-hover:text-slate-400 font-medium">Add Video</span>
            </div>
          </div>
        </div>

        {/* Right: Ground Truth Injection (Aligned Height, Compact Grid) */}
        <div className="w-80 min-w-[320px] p-4 flex flex-col bg-slate-950 border-l border-slate-800 shadow-inner">
           <div className="flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
             <span className="flex items-center gap-2">
                <Database className="text-rose-500" size={14} />
                GT Registry
             </span>
             <button onClick={onUploadGT} className="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded flex items-center gap-1 transition-colors border border-slate-700">
               <Upload size={10} /> Sync JSONs
             </button>
           </div>
           
           <div className="flex-1 bg-[#0f1115] rounded-lg border border-slate-800/60 p-3 overflow-hidden flex flex-col relative">
              <div className="absolute top-0 right-0 p-1">
                 <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
              </div>
              <div className="overflow-y-auto pr-1 h-full custom-scrollbar">
                  <div className="grid grid-cols-5 gap-2 auto-rows-min">
                    {videos.map((vid, i) => (
                        <div 
                            key={`gt-file-${vid.id}`} 
                            title={vid.hasGT ? `${vid.name}\n(Mapped)` : `Missing GT for ${vid.name}`}
                            className={`aspect-square rounded-md flex flex-col items-center justify-center gap-1 border transition-all cursor-help relative group overflow-hidden
                                ${vid.hasGT 
                                    ? 'bg-slate-800/80 border-slate-600 text-slate-300 hover:border-emerald-500 hover:text-emerald-400' 
                                    : 'bg-slate-900 border-slate-800 text-slate-700'
                                }
                            `}
                        >
                            <FileJson size={14} className={vid.hasGT ? "opacity-100" : "opacity-30"} />
                            <span className="text-[8px] font-mono leading-none opacity-60">#{String(i+1).padStart(2, '0')}</span>
                            
                            {vid.hasGT && (
                                <div className="absolute top-0.5 right-0.5 w-1.5 h-1.5 bg-emerald-500 rounded-full ring-2 ring-slate-900" />
                            )}
                        </div>
                    ))}
                    {/* Placeholder slots to show "capacity" */}
                    {Array.from({ length: Math.max(0, 10 - videos.length) }).map((_, i) => (
                         <div key={`ghost-${i}`} className="aspect-square rounded border border-dashed border-slate-800/50 flex items-center justify-center text-slate-800">
                            <div className="w-1 h-1 rounded-full bg-slate-800" />
                         </div>
                    ))}
                  </div>
              </div>
              <div className="mt-2 pt-2 border-t border-slate-800 text-[9px] text-slate-500 text-center font-mono">
                 Auto-mapped by filename
              </div>
           </div>
        </div>

      </div>
    </div>
  );
};

export default TopBar;
