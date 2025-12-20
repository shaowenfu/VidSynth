import React, { useEffect, useRef, useState } from 'react';
import { LogEntry } from '../types';
import { Terminal, Cpu, Settings, Play, RefreshCw, Sliders } from 'lucide-react';

interface Step3Props {
  logs: LogEntry[];
  theme: string | null;
  themeSlug: string | null;
  videoId: string | null;
  onSequenceComplete?: () => void;
}

const Step3Log: React.FC<Step3Props> = ({
  logs: initialLogs,
  theme,
  themeSlug,
  videoId,
  onSequenceComplete,
}) => {
  const [internalLogs, setInternalLogs] = useState<LogEntry[]>(initialLogs);
  const scrollRef = useRef<HTMLDivElement>(null);

  const [params, setParams] = useState({
    upperThreshold: 0.2,
    lowerThreshold: 0.21,
    minDuration: 2.0,
    maxDuration: 6.0,
    mergeGap: 1.0,
  });

  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const apiBase = import.meta.env.VITE_API_BASE || '';
  const resolveApiPath = (path: string) => (apiBase ? `${apiBase}${path}` : path);

  useEffect(() => {
    setInternalLogs(initialLogs);
  }, [initialLogs]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [internalLogs]);

  useEffect(() => {
    const source = new EventSource(resolveApiPath('/api/events'));
    const handleMessage = (event: MessageEvent) => {
      if (!event.data) {
        return;
      }
      try {
        const message = JSON.parse(event.data);
        if (message?.stage !== 'sequence' && message?.stage !== 'export') {
          return;
        }
        if (theme && message.theme && message.theme !== theme) {
          return;
        }
        if (videoId && message.video_id && message.video_id !== videoId) {
          return;
        }
        const status = message.status as string | undefined;
        if (message.stage === 'sequence') {
          if (status === 'queued' || status === 'running') {
            setIsProcessing(true);
          }
          if (status === 'done' || status === 'cached' || status === 'error') {
            setIsProcessing(false);
            setProgress(100);
          }
          if (typeof message.progress === 'number') {
            setProgress(Math.round(message.progress * 100));
          }
          if ((status === 'done' || status === 'cached') && onSequenceComplete) {
            onSequenceComplete();
          }
        }
        if (typeof message.message === 'string' && message.message) {
          addLog(classifyLogType(message.stage, message.message), formatMessage(message.stage, message.message));
        }
        if (status === 'error') {
          setStatusMessage(message.message || 'Sequence failed');
        }
      } catch (error) {
        return;
      }
    };
    source.onmessage = handleMessage;
    source.onerror = () => {
      setStatusMessage('SSE connection lost');
    };
    return () => source.close();
  }, [theme, videoId, apiBase, onSequenceComplete]);

  const handleRunStrategy = async () => {
    if (isProcessing) {
      return;
    }
    if (!theme || !themeSlug || !videoId) {
      setStatusMessage('Missing theme or video selection.');
      return;
    }
    setStatusMessage(null);
    setIsProcessing(true);
    setProgress(0);
    setInternalLogs([]);
    try {
      const response = await fetch(resolveApiPath('/api/sequence'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          theme,
          theme_slug: themeSlug,
          params: {
            upper_threshold: params.upperThreshold,
            lower_threshold: params.lowerThreshold,
            min_duration: params.minDuration,
            max_duration: params.maxDuration,
            merge_gap: params.mergeGap,
          },
          force: false,
          video_ids: [videoId],
        }),
      });
      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }
      const payload = await response.json();
      if (payload.status === 'cached') {
        setIsProcessing(false);
        setProgress(100);
        onSequenceComplete?.();
      }
      if (payload.status === 'skipped') {
        setIsProcessing(false);
      }
    } catch (error) {
      setIsProcessing(false);
      const message = error instanceof Error ? error.message : 'Sequence failed';
      setStatusMessage(message);
      addLog('error', message);
    }
  };

  const addLog = (type: LogEntry['type'], message: string) => {
    const newLog: LogEntry = {
      id: `${Date.now()}_${Math.random()}`,
      type,
      message,
      timestamp: new Date().toLocaleTimeString([], {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }),
    };
    setInternalLogs((prev) => [...prev, newLog]);
  };

  const handleChange = (key: keyof typeof params, value: string) => {
    setParams((prev) => ({ ...prev, [key]: parseFloat(value) }));
  };

  const isReady = Boolean(theme && themeSlug && videoId);

  return (
    <section className="mb-12 border-b border-slate-800 pb-12 snap-start scroll-mt-6">
      <div className="flex items-center gap-3 mb-6 px-6">
        <div className="w-8 h-8 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-sm">03</div>
        <h2 className="text-xl font-bold text-slate-100">Strategy Blackbox</h2>
        <span className="text-xs text-slate-500 uppercase tracking-wide border border-slate-700 px-2 py-0.5 rounded">Logic & Serialization</span>
      </div>

      <div className="px-6 grid grid-cols-10 gap-6 h-[450px]">
        <div className="col-span-3 bg-slate-900 rounded-lg border border-slate-800 p-5 flex flex-col shadow-lg">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-5 pb-2 border-b border-slate-800/50">
            <Settings size={14} /> Configuration
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto pr-1 custom-scrollbar">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-[10px] text-slate-500 font-bold uppercase">Upper Threshold</label>
                <input
                  type="number"
                  step="0.01"
                  value={params.upperThreshold}
                  onChange={(e) => handleChange('upperThreshold', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:border-cyan-500 outline-none transition-colors font-mono"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-slate-500 font-bold uppercase">Lower Threshold</label>
                <input
                  type="number"
                  step="0.01"
                  value={params.lowerThreshold}
                  onChange={(e) => handleChange('lowerThreshold', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:border-cyan-500 outline-none transition-colors font-mono"
                />
              </div>
            </div>

            <div className="space-y-1 pt-2 border-t border-slate-800/50">
              <label className="text-[10px] text-slate-500 font-bold uppercase flex justify-between">
                <span>Min Duration (s)</span>
              </label>
              <input
                type="number"
                step="0.1"
                value={params.minDuration}
                onChange={(e) => handleChange('minDuration', e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:border-cyan-500 outline-none transition-colors font-mono"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] text-slate-500 font-bold uppercase">Max Duration (s)</label>
              <input
                type="number"
                step="0.1"
                value={params.maxDuration}
                onChange={(e) => handleChange('maxDuration', e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:border-cyan-500 outline-none transition-colors font-mono"
              />
            </div>

            <div className="space-y-1 pt-2 border-t border-slate-800/50">
              <label className="text-[10px] text-slate-500 font-bold uppercase flex items-center gap-1">
                <Sliders size={10} /> Merge Gap (s)
              </label>
              <input
                type="number"
                step="0.1"
                value={params.mergeGap}
                onChange={(e) => handleChange('mergeGap', e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-xs text-cyan-300 focus:border-cyan-500 outline-none transition-colors font-mono border-l-4 border-l-cyan-500/50"
              />
              <p className="text-[9px] text-slate-600 leading-tight">Gaps smaller than this will be merged into a single segment.</p>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-800">
            {isProcessing ? (
              <div className="space-y-2">
                <div className="flex justify-between text-[10px] text-amber-500 font-bold uppercase">
                  <span>Serializing...</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <div className="h-1.5 w-full bg-slate-950 rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500 transition-all duration-100" style={{ width: `${progress}%` }}></div>
                </div>
              </div>
            ) : (
              <button
                onClick={handleRunStrategy}
                disabled={!isReady}
                className={`w-full py-2 rounded text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
                  isReady
                    ? 'bg-amber-600/20 hover:bg-amber-600/30 text-amber-500 border border-amber-600/50 hover:border-amber-500'
                    : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
                }`}
              >
                <Play size={12} fill="currentColor" /> Run Strategy
              </button>
            )}
            {statusMessage && (
              <div className="mt-2 text-[10px] text-rose-400">
                {statusMessage}
              </div>
            )}
          </div>
        </div>

        <div className="col-span-7 bg-black rounded-lg border border-slate-800 p-4 font-mono text-xs shadow-inner flex flex-col relative overflow-hidden">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-2 mb-2 text-slate-500 select-none">
            <Terminal size={14} />
            <span>pipeline_output.stream</span>
            {isProcessing ? (
              <div className="ml-auto flex items-center gap-2">
                <span className="text-amber-500 animate-pulse">●</span>
                <Cpu size={12} className="text-slate-400" />
              </div>
            ) : (
              <div className="ml-auto flex items-center gap-2 cursor-pointer hover:text-slate-300" onClick={() => setInternalLogs([])}>
                <RefreshCw size={12} />
                <span className="text-[10px]">Clear</span>
              </div>
            )}
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-1.5 pr-2 custom-scrollbar relative z-10">
            {internalLogs.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center opacity-20 pointer-events-none">
                <span className="text-4xl font-bold text-slate-700">NO LOGS</span>
              </div>
            )}
            {internalLogs.map((log) => {
              let colorClass = 'text-slate-300';
              let bgClass = '';

              if (log.type === 'filter') {
                colorClass = 'text-rose-400';
                bgClass = 'bg-rose-950/10';
              }
              if (log.type === 'merge') {
                colorClass = 'text-cyan-400';
                bgClass = 'bg-cyan-950/10';
              }
              if (log.type === 'result') {
                colorClass = 'text-emerald-400 font-bold';
                bgClass = 'bg-emerald-950/20 border-l-2 border-emerald-500 pl-2';
              }
              if (log.type === 'info') {
                colorClass = 'text-slate-400';
              }
              if (log.type === 'error') {
                colorClass = 'text-rose-400 font-bold';
                bgClass = 'bg-rose-950/30 border-l-2 border-rose-500 pl-2';
              }

              return (
                <div key={log.id} className={`flex gap-3 p-0.5 rounded ${bgClass} animate-in fade-in slide-in-from-left-2 duration-300`}>
                  <span className="text-slate-600 min-w-[65px] opacity-70">{log.timestamp}</span>
                  <span className={`uppercase min-w-[50px] font-bold text-[10px] tracking-wider pt-0.5 ${colorClass.split(' ')[0]}`}>{log.type}</span>
                  <span className={`${colorClass} flex-1 break-all`}>{log.message}</span>
                </div>
              );
            })}

            {isProcessing && (
              <div className="flex gap-3 p-0.5 animate-pulse">
                <span className="text-slate-700 min-w-[65px]">--:--:--</span>
                <span className="text-slate-700 uppercase min-w-[50px]">...</span>
                <span className="text-amber-500/50">_</span>
              </div>
            )}
          </div>

          <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] z-[5] bg-[length:100%_2px,3px_100%] pointer-events-none opacity-20"></div>
        </div>
      </div>
    </section>
  );
};

const classifyLogType = (stage: string, message: string): LogEntry['type'] => {
  if (message.startsWith('FILTER')) {
    return 'filter';
  }
  if (message.startsWith('MERGE')) {
    return 'merge';
  }
  if (message.startsWith('RESULT')) {
    return 'result';
  }
  if (stage === 'export') {
    return 'info';
  }
  return 'info';
};

const formatMessage = (stage: string, message: string) => {
  if (stage === 'export' && !message.startsWith('EXPORT')) {
    return `EXPORT ${message}`;
  }
  return message;
};

export default Step3Log;
