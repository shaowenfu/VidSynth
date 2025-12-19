
import React, { useCallback, useEffect, useState } from 'react';
import Step1Segmentation from './components/Step1Segmentation';
import Step2Semantic from './components/Step2Semantic';
import Step3Log from './components/Step3Log';
import Step4FinalCut from './components/Step4FinalCut';
import ClusterSandbox from './components/ClusterSandbox';
import ProjectConfigModal from './components/ProjectConfigModal';
import { AssetRecord, VideoResource } from './types';
import { Zap, LayoutGrid, Box, Settings2 } from 'lucide-react';

const App: React.FC = () => {
  const [activeVideoId, setActiveVideoId] = useState<string | null>(null);
  const [videos, setVideos] = useState<VideoResource[]>([]);
  const [currentView, setCurrentView] = useState<'pipeline' | 'sandbox'>('pipeline');
  const [isProjectConfigOpen, setIsProjectConfigOpen] = useState(false);
  const [isLoadingAssets, setIsLoadingAssets] = useState(true);
  const [assetsError, setAssetsError] = useState<string | null>(null);

  const apiBase = import.meta.env.VITE_API_BASE || '';

  const resolveAssetUrl = (url?: string | null) => {
    if (!url) return '';
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    return `${apiBase}${url}`;
  };

  const mapAssetToVideo = (asset: AssetRecord): VideoResource => ({
    id: asset.id,
    name: asset.name,
    url: resolveAssetUrl(asset.video_url),
    thumbnail: resolveAssetUrl(asset.thumb_url),
    duration: asset.duration ?? 0,
    hasGT: asset.hasGT,
    status: asset.status ?? (asset.segmented ? 'ready' : 'idle'),
    groundTruth: undefined,
    predictedSegments: [],
    segmented: asset.segmented,
    clipsUrl: resolveAssetUrl(asset.clips_url) || null,
    gtUrl: resolveAssetUrl(asset.gt_url) || null,
    progress: asset.progress ?? null,
  });

  const refreshAssets = useCallback(async () => {
    setIsLoadingAssets(true);
    setAssetsError(null);
    try {
      const response = await fetch(`${apiBase}/api/assets`);
      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }
      const payload = (await response.json()) as AssetRecord[];
      const nextVideos = payload.map(mapAssetToVideo);
      setVideos(nextVideos);
      setActiveVideoId((prev) => {
        if (nextVideos.length === 0) {
          return null;
        }
        if (prev && nextVideos.some((video) => video.id === prev)) {
          return prev;
        }
        return nextVideos[0].id;
      });
    } catch (error) {
      setAssetsError(error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setIsLoadingAssets(false);
    }
  }, [apiBase]);

  useEffect(() => {
    refreshAssets();
  }, [refreshAssets]);

  // Derive active video object
  const activeVideo = activeVideoId
    ? videos.find((v) => v.id === activeVideoId)
    : undefined;

  return (
    <div className="h-screen bg-[#050505] text-slate-200 font-sans p-4 flex items-center justify-center overflow-hidden">
      
      {/* Decorative Outer Container */}
      <div className="w-full h-full max-w-[1920px] bg-slate-950 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden relative">
        
        {/* App Header & Navigation */}
        <header className="h-16 bg-slate-950/80 backdrop-blur border-b border-slate-800 flex items-center justify-between px-6 shrink-0 z-50">
           <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/20">
                 <Zap className="text-white fill-white" size={18} />
              </div>
              <h1 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
                VidSynth Visualizer
              </h1>
              <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-500 border border-slate-700 ml-2">v0.9.1-beta</span>
           </div>

           <div className="flex items-center gap-4">
               {/* Project Settings Button */}
               <button 
                  onClick={() => setIsProjectConfigOpen(true)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors border border-transparent hover:border-slate-700"
                >
                  <Settings2 size={14} />
                  Project Config
               </button>

               <div className="h-6 w-px bg-slate-800 mx-1" />

               <nav className="flex items-center gap-1 bg-slate-900/50 p-1 rounded-lg border border-slate-800">
                  <button 
                    onClick={() => setCurrentView('pipeline')}
                    className={`
                      flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-semibold transition-all
                      ${currentView === 'pipeline' 
                        ? 'bg-slate-800 text-white shadow-sm ring-1 ring-slate-700' 
                        : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50'
                      }
                    `}
                  >
                    <LayoutGrid size={16} />
                    Main Pipeline
                  </button>
                  <button 
                    onClick={() => setCurrentView('sandbox')}
                    className={`
                      flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-semibold transition-all
                      ${currentView === 'sandbox' 
                        ? 'bg-slate-800 text-white shadow-sm ring-1 ring-slate-700' 
                        : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50'
                      }
                    `}
                  >
                    <Box size={16} />
                    Cluster Sandbox
                  </button>
               </nav>
           </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 overflow-hidden relative">
          
          {currentView === 'pipeline' ? (
             <div className="h-full flex flex-col overflow-hidden animate-in fade-in duration-300">
                {activeVideo ? (
                  <div className="flex-1 overflow-y-auto custom-scrollbar pt-6 pb-20 snap-y snap-mandatory scroll-pt-6">
                      <div className="space-y-12">
                        <Step1Segmentation 
                          video={activeVideo} 
                          allVideos={videos}
                          onSelectVideo={setActiveVideoId}
                        />
                        <Step2Semantic videos={videos} />
                        <Step3Log logs={[]} />
                        <Step4FinalCut video={activeVideo} />
                      </div>
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-sm text-slate-500">
                    {isLoadingAssets
                      ? 'Loading assets...'
                      : assetsError
                        ? `Failed to load assets: ${assetsError}`
                        : 'No videos found. Upload in Project Config.'}
                  </div>
                )}
             </div>
          ) : (
             <div className="h-full w-full">
                <ClusterSandbox />
             </div>
          )}

        </main>
        
        {/* Project Config Modal */}
        <ProjectConfigModal 
          isOpen={isProjectConfigOpen}
          onClose={() => setIsProjectConfigOpen(false)}
          videos={videos}
          activeVideoId={activeVideoId}
          onSelectVideo={setActiveVideoId}
          onRefreshAssets={refreshAssets}
        />

      </div>
    </div>
  );
};

export default App;
