import React, { useMemo, useState, useRef, useEffect } from 'react';
import { Terminal, X, Trash2, Search, ArrowDownCircle, PauseCircle, PlayCircle, Filter } from 'lucide-react';
import { useLogStore } from '../context/LogContext';
import { LogLevel, LogStage } from '../types';

interface LogConsoleModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const LogConsoleModal: React.FC<LogConsoleModalProps> = ({ isOpen, onClose }) => {
  const { logs, clearLogs, isConnected, statusByStage } = useLogStore();
  const [filterText, setFilterText] = useState('');
  const [activeLevels, setActiveLevels] = useState<Set<LogLevel>>(new Set(['INFO', 'WARNING', 'ERROR']));
  const [activeStage, setActiveStage] = useState<LogStage | 'ALL'>('ALL');
  const [autoScroll, setAutoScroll] = useState(true);
  const [showStatusLogs, setShowStatusLogs] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logic
  useEffect(() => {
    if (autoScroll && isOpen && bottomRef.current) {
        bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll, isOpen]);

  const toggleLevel = (level: LogLevel) => {
    const next = new Set(activeLevels);
    if (next.has(level)) next.delete(level);
    else next.add(level);
    setActiveLevels(next);
  };

  const visibleLogs = useMemo(() => {
    return logs.filter(log => 
      activeLevels.has(log.level) && 
      (activeStage === 'ALL' || log.stage === activeStage) &&
      (showStatusLogs || log.context?.source !== 'status') &&
      log.message.toLowerCase().includes(filterText.toLowerCase())
    );
  }, [logs, filterText, activeLevels, activeStage, showStatusLogs]);

  if (!isOpen) return null;

  const getLevelColor = (level: LogLevel) => {
      switch(level) {
          case 'ERROR': return 'text-rose-500';
          case 'WARNING': return 'text-amber-400';
          case 'DEBUG': return 'text-slate-500';
          default: return 'text-blue-400';
      }
  };

  const getStageColor = (stage: LogStage) => {
      switch(stage) {
          case 'segmentation': return 'text-cyan-400';
          case 'matching': return 'text-purple-400';
          case 'sequencing': return 'text-emerald-400';
          case 'export': return 'text-orange-400';
          default: return 'text-slate-400';
      }
  };

  const stageCards: { stage: LogStage; label: string }[] = [
    { stage: 'segmentation', label: 'Segmentation' },
    { stage: 'matching', label: 'Matching' },
    { stage: 'sequencing', label: 'Sequencing' },
    { stage: 'export', label: 'Export' },
  ];

  const formatProgress = (value: number | null | undefined) => {
    if (value === null || value === undefined) {
      return '--%';
    }
    return `${value}%`;
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-950 w-[1000px] h-[85vh] rounded-2xl border border-slate-700 shadow-2xl flex flex-col overflow-hidden relative animate-in zoom-in-95 duration-200 ring-1 ring-white/10">
        
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-900/80">
           <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <Terminal className="text-slate-400" size={16} />
              System Console
              <span className={`text-[10px] px-1.5 py-0.5 rounded border ${isConnected ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10' : 'border-rose-500/30 text-rose-400 bg-rose-500/10'}`}>
                  {isConnected ? 'LIVE' : 'DISCONNECTED'}
              </span>
           </h2>
           <button onClick={onClose} className="p-1.5 hover:bg-slate-800 rounded-md transition-colors text-slate-400 hover:text-white">
             <X size={18} />
           </button>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-3 p-2 bg-slate-900 border-b border-slate-800 text-xs">
           
           {/* Level Toggles */}
           <div className="flex bg-slate-950 rounded-md p-0.5 border border-slate-800">
              {(['DEBUG', 'INFO', 'WARNING', 'ERROR'] as LogLevel[]).map(lvl => (
                  <button
                    key={lvl}
                    onClick={() => toggleLevel(lvl)}
                    className={`px-2 py-1 rounded transition-colors font-medium ${
                        activeLevels.has(lvl) 
                        ? 'bg-slate-800 text-white shadow-sm' 
                        : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {lvl}
                  </button>
              ))}
           </div>

           <div className="h-4 w-px bg-slate-800 mx-1" />

           {/* Stage Filter */}
           <div className="relative group">
               <select 
                 value={activeStage} 
                 onChange={(e) => setActiveStage(e.target.value as any)}
                 className="appearance-none bg-slate-950 border border-slate-800 text-slate-300 pl-8 pr-8 py-1.5 rounded focus:outline-none focus:border-slate-600 hover:border-slate-700 transition-colors"
               >
                  <option value="ALL">All Stages</option>
                  <option value="segmentation">Segmentation</option>
                  <option value="matching">Theme Matching</option>
                  <option value="sequencing">Sequencing</option>
                  <option value="export">Export</option>
                  <option value="clustering">Clustering</option>
                  <option value="system">System</option>
               </select>
               <Filter className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" size={12} />
           </div>

           <button
             onClick={() => setShowStatusLogs((prev) => !prev)}
             className={`px-2 py-1 rounded border text-[10px] font-semibold uppercase tracking-wide transition-colors ${
               showStatusLogs
                 ? 'border-cyan-500/50 text-cyan-300 bg-cyan-500/10'
                 : 'border-slate-700 text-slate-500'
             }`}
           >
             Status Logs
           </button>

           {/* Search */}
           <div className="relative flex-1 max-w-xs">
               <input 
                 value={filterText}
                 onChange={(e) => setFilterText(e.target.value)}
                 placeholder="Filter logs..."
                 className="w-full bg-slate-950 border border-slate-800 text-slate-300 pl-8 pr-2 py-1.5 rounded focus:outline-none focus:border-cyan-500/50 placeholder:text-slate-600"
               />
               <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" size={12} />
           </div>

           <div className="flex-1" />

           {/* Actions */}
           <button 
             onClick={() => setAutoScroll(!autoScroll)}
             title={autoScroll ? "Pause Auto-scroll" : "Enable Auto-scroll"}
             className={`p-1.5 rounded transition-colors ${autoScroll ? 'text-emerald-400 bg-emerald-500/10' : 'text-slate-500 hover:text-slate-300'}`}
           >
             {autoScroll ? <PauseCircle size={16} /> : <PlayCircle size={16} />}
           </button>

           <button 
             onClick={clearLogs} 
             title="Clear Console"
             className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded transition-colors"
           >
             <Trash2 size={16} />
           </button>
        </div>

        {/* Stage Overview */}
        <div className="grid grid-cols-4 gap-2 px-4 py-3 bg-[#0b0b0d] border-b border-slate-800 text-[10px]">
          {stageCards.map((card) => {
            const snapshot = statusByStage[card.stage];
            const status = snapshot?.status?.toUpperCase() || 'IDLE';
            const progress = snapshot?.progress ?? null;
            const themeSlug = snapshot?.theme_slug;
            return (
              <div key={card.stage} className="bg-slate-950 border border-slate-800 rounded-lg p-2 flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className={`font-semibold ${getStageColor(card.stage)}`}>{card.label}</span>
                  <span className="text-[9px] text-slate-500">{status}</span>
                </div>
                <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-slate-400"
                    style={{ width: `${progress ?? 0}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-[9px] text-slate-500">
                  <span>{formatProgress(progress)}</span>
                  <span className="truncate max-w-[90px]">{themeSlug || ''}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Console Content */}
        <div className="flex-1 overflow-y-auto bg-[#050505] p-4 font-mono text-[11px] leading-relaxed custom-scrollbar selection:bg-cyan-500/30">
            {visibleLogs.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-600 gap-2">
                    <Terminal size={32} className="opacity-20" />
                    <span>No logs found matching filters</span>
                </div>
            ) : (
                visibleLogs.map(log => (
                <div key={log.id} className={`flex gap-3 mb-0.5 p-1 rounded hover:bg-white/5 transition-colors group ${
                  log.level === 'ERROR' ? 'bg-rose-950/10 border-l-2 border-rose-900/50 pl-2' : ''
                }`}>
                    
                    {/* Timestamp */}
                    <span className="text-slate-600 w-20 shrink-0 select-none">
                        {new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit', fractionalSecondDigits: 3 })}
                    </span>
                    
                    {/* Level */}
                    <span className={`w-10 shrink-0 font-bold ${getLevelColor(log.level)}`}>
                        {log.level}
                    </span>
                    
                    {/* Stage */}
                    <span className={`w-24 shrink-0 truncate text-right ${getStageColor(log.stage)} opacity-80`}>
                        [{log.stage}]
                    </span>
                    
                    {/* Message */}
                    <div className="flex-1 text-slate-300 break-all">
                        {log.message}
                        
                        {/* Context Data (Interactive) */}
                        {log.context && Object.keys(log.context).length > 0 && (
                            <details className="mt-1 ml-2 inline-block">
                                <summary className="cursor-pointer text-slate-500 hover:text-cyan-400 select-none text-[10px] bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                                    payload
                                </summary>
                                <pre className="mt-2 p-2 bg-slate-900/80 rounded border border-slate-800 text-slate-400 overflow-x-auto text-[10px]">
                                    {JSON.stringify(log.context, null, 2)}
                                </pre>
                            </details>
                        )}
                    </div>
                </div>
                ))
            )}
            
            <div ref={bottomRef} className="h-4" />
        </div>
        
        {/* Footer/Status Bar */}
        <div className="bg-slate-900 border-t border-slate-800 px-3 py-1 text-[10px] text-slate-500 flex justify-between">
            <span>{visibleLogs.length} visible / {logs.length} total</span>
            <span>VidSynth Logging Protocol v1.0</span>
        </div>

      </div>
    </div>
  );
};

export default LogConsoleModal;
