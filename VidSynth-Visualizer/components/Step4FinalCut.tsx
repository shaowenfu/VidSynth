import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { VideoResource, EdlEntry } from '../types';
import { Clapperboard, Download, Scissors } from 'lucide-react';

interface Step4Props {
  video: VideoResource;
  theme: string | null;
  themeSlug: string | null;
  refreshKey?: number;
}

const Step4FinalCut: React.FC<Step4Props> = ({ video, theme, themeSlug, refreshKey }) => {
  const [edlItems, setEdlItems] = useState<EdlEntry[]>([]);
  const [edlError, setEdlError] = useState<string | null>(null);
  const [exportStatus, setExportStatus] = useState<'idle' | 'queued' | 'running' | 'cached' | 'done' | 'error'>('idle');
  const [exportProgress, setExportProgress] = useState(0);
  const [exportMessage, setExportMessage] = useState<string | null>(null);
  const [exportNonce, setExportNonce] = useState(Date.now());
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const apiBase = import.meta.env.VITE_API_BASE || '';
  const resolveApiPath = (path: string) => (apiBase ? `${apiBase}${path}` : path);

  const outputBase = themeSlug ? resolveApiPath(`/static/exports/${themeSlug}/${video.id}/output.mp4`) : '';
  const outputUrl = outputBase ? `${outputBase}?t=${exportNonce}` : '';

  const fetchEdl = useCallback(async () => {
    if (!themeSlug) {
      setEdlItems([]);
      return;
    }
    setEdlError(null);
    try {
      const response = await fetch(resolveApiPath(`/api/sequence/${themeSlug}/${video.id}/edl`));
      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }
      const payload = await response.json();
      if (!Array.isArray(payload)) {
        throw new Error('Invalid EDL payload');
      }
      let cursor = 0;
      const items: EdlEntry[] = payload.map((entry: any, index: number) => {
        const tStart = Number(entry.t_start ?? entry.tStart ?? 0);
        const tEnd = Number(entry.t_end ?? entry.tEnd ?? 0);
        const duration = Number(entry.duration ?? Math.max(0, tEnd - tStart));
        const timelineStart = cursor;
        const timelineEnd = timelineStart + duration;
        cursor = timelineEnd;
        return {
          index: Number(entry.index ?? index + 1),
          sourceVideoId: String(entry.source_video_id ?? entry.sourceVideoId ?? video.id),
          tStart,
          tEnd,
          duration,
          reason: entry.reason ? String(entry.reason) : undefined,
          timelineStart,
          timelineEnd,
        };
      });
      setEdlItems(items);
    } catch (error) {
      setEdlError(error instanceof Error ? error.message : 'Failed to load EDL');
      setEdlItems([]);
    }
  }, [themeSlug, video.id, apiBase]);

  const fetchExportStatus = useCallback(async () => {
    if (!themeSlug) {
      setExportStatus('idle');
      setExportProgress(0);
      setExportMessage(null);
      return;
    }
    try {
      const response = await fetch(resolveApiPath(`/api/export/${themeSlug}/${video.id}`));
      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }
      const payload = await response.json();
      if (payload?.status) {
        setExportStatus(payload.status);
        if (typeof payload.progress === 'number') {
          setExportProgress(Math.round(payload.progress * 100));
        }
        if (payload.result_path) {
          setExportNonce(Date.now());
        }
      }
    } catch (error) {
      setExportMessage(error instanceof Error ? error.message : 'Export status error');
    }
  }, [themeSlug, video.id, apiBase]);

  useEffect(() => {
    fetchEdl();
  }, [fetchEdl, refreshKey]);

  useEffect(() => {
    fetchExportStatus();
  }, [fetchExportStatus]);

  useEffect(() => {
    setExportNonce(Date.now());
  }, [themeSlug, video.id]);

  useEffect(() => {
    const source = new EventSource(resolveApiPath('/api/events'));
    const handleMessage = (event: MessageEvent) => {
      if (!event.data) {
        return;
      }
      try {
        const message = JSON.parse(event.data);
        if (message?.stage !== 'export') {
          return;
        }
        if (theme && message.theme && message.theme !== theme) {
          return;
        }
        if (message.video_id && message.video_id !== video.id) {
          return;
        }
        const status = message.status as typeof exportStatus | undefined;
        if (status) {
          setExportStatus(status);
        }
        if (typeof message.progress === 'number') {
          setExportProgress(Math.round(message.progress * 100));
        }
        if (typeof message.message === 'string' && message.message) {
          setExportMessage(message.message);
        }
        if ((status === 'done' || status === 'cached') && message.result_path) {
          setExportNonce(Date.now());
        }
      } catch (error) {
        return;
      }
    };
    source.onmessage = handleMessage;
    source.onerror = () => {
      setExportMessage('SSE connection lost');
    };
    return () => source.close();
  }, [theme, video.id, apiBase]);

  const handleExport = async () => {
    if (!theme || !themeSlug) {
      setExportMessage('Missing theme selection.');
      return;
    }
    setExportStatus('queued');
    setExportProgress(0);
    setExportMessage(null);
    try {
      const response = await fetch(resolveApiPath('/api/export'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          theme,
          theme_slug: themeSlug,
          video_id: video.id,
          force: false,
        }),
      });
      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }
      const payload = await response.json();
      if (payload.status === 'cached' && payload.result_path) {
        setExportStatus('cached');
        setExportProgress(100);
        setExportNonce(Date.now());
      }
    } catch (error) {
      setExportStatus('error');
      setExportMessage(error instanceof Error ? error.message : 'Export failed');
    }
  };

  const handleDownload = () => {
    if (!outputBase) {
      return;
    }
    const anchor = document.createElement('a');
    anchor.href = `${outputBase}?download=true&t=${Date.now()}`;
    anchor.download = `vidsynth_${themeSlug ?? 'theme'}_${video.id}.mp4`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  };

  const hasOutput = exportStatus === 'done' || exportStatus === 'cached';

  const totalDuration = useMemo(() => {
    if (edlItems.length === 0) {
      return 0;
    }
    const last = edlItems[edlItems.length - 1];
    return last.timelineEnd ?? edlItems.reduce((acc, item) => acc + (item.duration || 0), 0);
  }, [edlItems]);

  const formatTime = (time: number) => {
    const m = Math.floor(time / 60);
    const s = Math.floor(time % 60);
    const ms = Math.floor((time % 1) * 100);
    return `${m}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
  };

  const handleEdlClick = (entry: EdlEntry) => {
    setSelectedIndex(entry.index);
    if (videoRef.current && entry.timelineStart !== undefined) {
      videoRef.current.currentTime = entry.timelineStart;
      videoRef.current.play().catch(() => null);
    }
  };

  return (
    <section className="mb-24 px-6 snap-start scroll-mt-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-sm">04</div>
          <h2 className="text-xl font-bold text-slate-100">Final Cut</h2>
          {exportMessage && (
            <span className="text-xs text-rose-400">{exportMessage}</span>
          )}
        </div>
        {hasOutput ? (
          <button
            onClick={handleDownload}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 shadow-lg shadow-indigo-500/20 transition-all"
          >
            <Download size={16} /> Download
          </button>
        ) : (
          <button
            onClick={handleExport}
            disabled={exportStatus === 'queued' || exportStatus === 'running'}
            className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 shadow-lg transition-all ${
              exportStatus === 'queued' || exportStatus === 'running'
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-500/20'
            }`}
          >
            <Download size={16} /> Export Video
          </button>
        )}
      </div>

      <div className="flex flex-col xl:flex-row gap-6 h-[500px]">
        <div className="flex-1 bg-black rounded-xl border border-slate-800 shadow-2xl relative overflow-hidden group">
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            {!hasOutput && (
              <span className="text-slate-700 font-mono text-sm tracking-widest uppercase">Awaiting Export</span>
            )}
          </div>
          <video
            ref={videoRef}
            className={`w-full h-full object-contain ${hasOutput ? 'opacity-100' : 'opacity-40'}`}
            src={outputUrl || undefined}
            controls
          />

          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-slate-900/80 backdrop-blur rounded-full px-6 py-2 border border-white/10 flex items-center gap-4">
            <button className="text-white hover:text-cyan-400">
              <Scissors size={18} />
            </button>
            <div className="w-64 h-1 bg-slate-600 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-500" style={{ width: `${Math.min(exportProgress, 100)}%` }} />
            </div>
            <span className="text-xs font-mono text-white">
              {Math.round(exportProgress)}%
            </span>
          </div>
        </div>

        <div className="w-full xl:w-96 bg-slate-900 rounded-xl border border-slate-800 flex flex-col overflow-hidden">
          <div className="p-4 border-b border-slate-800 bg-slate-950/30 flex justify-between items-center">
            <h3 className="text-sm font-bold text-slate-300 flex items-center gap-2">
              <Clapperboard size={14} /> EDL (Edit Decision List)
            </h3>
            <span className="text-[10px] text-slate-500">{edlItems.length} Segments</span>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {edlError && (
              <div className="text-[10px] text-rose-400 p-2">{edlError}</div>
            )}
            {edlItems.length === 0 && !edlError && (
              <div className="text-[10px] text-slate-500 p-2">No EDL data yet.</div>
            )}
            {edlItems.map((item) => (
              <div
                key={`${item.sourceVideoId}-${item.index}`}
                onClick={() => handleEdlClick(item)}
                className={`flex items-center gap-3 p-3 rounded-lg transition-colors cursor-pointer group ${
                  selectedIndex === item.index ? 'bg-slate-800' : 'hover:bg-slate-800'
                }`}
              >
                <span className="text-xs font-mono text-slate-600 w-4">{item.index.toString().padStart(2, '0')}</span>
                <div className="w-12 h-8 bg-slate-800 rounded overflow-hidden flex items-center justify-center">
                  <span className="text-[9px] text-slate-500">CUT</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-mono text-slate-300">
                    {formatTime(item.tStart)} -&gt; {formatTime(item.tEnd)}
                  </span>
                  <span className="text-[10px] text-slate-500">Source: {video.name}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="p-3 border-t border-slate-800 bg-slate-950/30 text-center">
            <span className="text-[10px] text-slate-500 font-mono">Total Duration: {formatTime(totalDuration)}</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Step4FinalCut;
