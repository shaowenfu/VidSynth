
import React, { useEffect, useRef, useState } from 'react';
import { Upload, FileJson, CheckCircle, Plus, Database, X, Scissors } from 'lucide-react';
import { VideoResource } from '../types';

interface ProjectConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  videos: VideoResource[];
  activeVideoId: string | null;
  onSelectVideo: (id: string) => void;
  onRefreshAssets: () => Promise<void>;
}

const ProjectConfigModal: React.FC<ProjectConfigModalProps> = ({ 
  isOpen, onClose, videos, activeVideoId, onSelectVideo, onRefreshAssets 
}) => {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedSegmentIds, setSelectedSegmentIds] = useState<string[]>([]);
  const [isSegmenting, setIsSegmenting] = useState(false);
  const [segmentError, setSegmentError] = useState<string | null>(null);
  const apiBase = import.meta.env.VITE_API_BASE || '';

  const handleAddSources = () => {
    if (isUploading) return;
    inputRef.current?.click();
  };

  const handleFilesSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files: File[] = event.target.files ? Array.from(event.target.files) : [];
    if (files.length === 0) {
      return;
    }
    setIsUploading(true);
    setUploadError(null);
    try {
      const formData = new FormData();
      files.forEach((file) => formData.append('files', file));
      const response = await fetch(`${apiBase}/api/import/videos`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }
      await onRefreshAssets();
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setIsUploading(false);
      event.target.value = '';
    }
  };

  const handleSync = async () => {
    if (isUploading) return;
    await onRefreshAssets();
  };

  useEffect(() => {
    setSelectedSegmentIds((prev) => prev.filter((id) => videos.some((video) => video.id === id)));
  }, [videos]);

  const handleSegmentRun = async (force: boolean) => {
    if (isUploading || isSegmenting || selectedSegmentIds.length === 0) {
      return;
    }
    setIsSegmenting(true);
    setSegmentError(null);
    try {
      const response = await fetch(`${apiBase}/api/segment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_ids: selectedSegmentIds, force }),
      });
      if (!response.ok) {
        throw new Error(`Segmentation failed: ${response.status}`);
      }
      await onRefreshAssets();
    } catch (error) {
      setSegmentError(error instanceof Error ? error.message : 'Segmentation failed');
    } finally {
      setIsSegmenting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-950 w-[900px] max-h-[80vh] rounded-2xl border border-slate-700 shadow-2xl flex flex-col overflow-hidden relative animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50">
           <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Database className="text-cyan-500" size={20} />
              Project Configuration
           </h2>
           <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400 hover:text-white">
             <X size={20} />
           </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
            
            {/* Section 1: Video Pool */}
            <section>
                <div className="flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                    <span className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                    Video Resource Pool ({videos.length})
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSelectedSegmentIds(videos.map((video) => video.id))}
                        className="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded transition-colors border border-slate-700"
                      >
                        Select All
                      </button>
                      <button
                        onClick={() => setSelectedSegmentIds([])}
                        className="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded transition-colors border border-slate-700"
                      >
                        Clear
                      </button>
                      <button
                        onClick={() => handleSegmentRun(false)}
                        disabled={isSegmenting || selectedSegmentIds.length === 0}
                        className="flex items-center gap-1 text-emerald-400 hover:text-emerald-300 bg-emerald-950/30 px-3 py-1.5 rounded transition-colors border border-emerald-900/50 disabled:opacity-40"
                      >
                        <Scissors size={12} /> {isSegmenting ? 'Segmenting...' : `Segment (${selectedSegmentIds.length})`}
                      </button>
                      <button
                        onClick={() => handleSegmentRun(true)}
                        disabled={isSegmenting || selectedSegmentIds.length === 0}
                        className="flex items-center gap-1 text-rose-300 hover:text-rose-200 bg-rose-950/30 px-3 py-1.5 rounded transition-colors border border-rose-900/50 disabled:opacity-40"
                      >
                        Force
                      </button>
                      <button
                        onClick={handleAddSources}
                        className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300 bg-cyan-950/30 px-3 py-1.5 rounded transition-colors border border-cyan-900/50 disabled:opacity-40"
                        disabled={isUploading}
                      >
                      <Upload size={12} /> {isUploading ? 'Uploading...' : 'Add Sources'}
                      </button>
                    </div>
                </div>

                <input
                  ref={inputRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={handleFilesSelected}
                />
                
                <div className="grid grid-cols-4 gap-4">
                    {videos.map((vid) => (
                    <div
                        key={vid.id}
                        onClick={() => onSelectVideo(vid.id)}
                        className={`relative group cursor-pointer transition-all ${
                        activeVideoId === vid.id 
                            ? 'ring-2 ring-cyan-500 rounded-lg scale-[1.02] shadow-xl shadow-cyan-900/20' 
                            : 'opacity-70 hover:opacity-100 hover:scale-[1.02]'
                        }`}
                    >
                        <label
                          className="absolute top-2 left-2 z-10 flex items-center gap-1 text-[10px] bg-black/50 px-1.5 py-0.5 rounded text-slate-200"
                          onClick={(event) => event.stopPropagation()}
                        >
                          <input
                            type="checkbox"
                            checked={selectedSegmentIds.includes(vid.id)}
                            onChange={() =>
                              setSelectedSegmentIds((prev) =>
                                prev.includes(vid.id)
                                  ? prev.filter((id) => id !== vid.id)
                                  : [...prev, vid.id]
                              )
                            }
                          />
                          <span>Select</span>
                        </label>
                        <div className="aspect-video bg-slate-800 rounded-lg overflow-hidden relative shadow-md">
                            <img src={vid.thumbnail} alt={vid.name} className="w-full h-full object-cover" />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/10 to-transparent" />
                            
                            {/* Info Badge */}
                            <div className="absolute bottom-2 left-2 right-2">
                                <div className="text-[11px] text-white font-medium truncate drop-shadow-md">{vid.name}</div>
                                <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-[10px] text-slate-300 bg-black/40 px-1.5 rounded backdrop-blur-sm font-mono">{vid.duration.toFixed(2)}s</span>
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
                                {vid.status === 'error' && (
                                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500 box-content border-2 border-black/50" />
                                )}
                            </div>

                            {(vid.status === 'running' || vid.status === 'queued') && typeof vid.progress === 'number' && (
                              <div className="absolute bottom-0 left-0 right-0 h-1 bg-black/60">
                                <div
                                  className="h-full bg-amber-400"
                                  style={{ width: `${Math.round(vid.progress * 100)}%` }}
                                />
                              </div>
                            )}
                            
                            {/* Selection Ring */}
                            {activeVideoId === vid.id && (
                                <div className="absolute inset-0 border-2 border-cyan-500 rounded-lg pointer-events-none" />
                            )}
                        </div>
                    </div>
                    ))}
                    
                    {/* Add placeholder */}
                    <div
                      onClick={handleAddSources}
                      className="aspect-video border-2 border-dashed border-slate-700/50 rounded-lg flex flex-col items-center justify-center gap-3 cursor-pointer hover:border-slate-500 hover:bg-slate-800/30 transition-colors group"
                    >
                        <div className="p-3 bg-slate-800 rounded-full group-hover:bg-slate-700 transition-colors">
                            <Plus className="text-slate-500 group-hover:text-slate-300" />
                        </div>
                        <span className="text-xs text-slate-600 group-hover:text-slate-400 font-medium">Add Video</span>
                    </div>
                </div>
                {uploadError && (
                  <div className="mt-3 text-[11px] text-rose-400">
                    {uploadError}
                  </div>
                )}
                {segmentError && (
                  <div className="mt-2 text-[11px] text-rose-400">
                    {segmentError}
                  </div>
                )}
            </section>

            <hr className="border-slate-800" />

            {/* Section 2: GT Registry */}
            <section>
                <div className="flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                    <span className="flex items-center gap-2">
                        <FileJson className="text-rose-500" size={14} />
                        GT Registry & Mapping
                    </span>
                    <button
                      onClick={handleSync}
                      className="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded flex items-center gap-1 transition-colors border border-slate-700 disabled:opacity-40"
                      disabled={isUploading}
                    >
                    <Upload size={10} /> Sync JSONs
                    </button>
                </div>
                
                <div className="bg-[#0f1115] rounded-lg border border-slate-800/60 p-4 relative">
                    <div className="grid grid-cols-8 gap-3">
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
                                <FileJson size={20} className={vid.hasGT ? "opacity-100" : "opacity-30"} />
                                <span className="text-[10px] font-mono leading-none opacity-60 mt-1">#{String(i+1).padStart(2, '0')}</span>
                                
                                {vid.hasGT && (
                                    <div className="absolute top-1 right-1 w-2 h-2 bg-emerald-500 rounded-full ring-2 ring-slate-900" />
                                )}
                            </div>
                        ))}
                    </div>
                    <div className="mt-4 pt-2 border-t border-slate-800 text-[10px] text-slate-500 flex justify-between">
                         <span>Status: {videos.filter(v => v.hasGT).length}/{videos.length} Mapped</span>
                         <span className="font-mono text-slate-600">Auto-mapped by filename</span>
                    </div>
                </div>
            </section>

        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/50 flex justify-end">
            <button onClick={onClose} className="bg-cyan-600 hover:bg-cyan-500 text-white px-6 py-2 rounded-lg text-sm font-semibold transition-colors">
                Done
            </button>
        </div>
      </div>
    </div>
  );
};

export default ProjectConfigModal;
