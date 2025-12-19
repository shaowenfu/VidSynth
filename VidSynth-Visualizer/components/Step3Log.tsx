
import React, { useState, useEffect, useRef } from 'react';
import { LogEntry } from '../types';
import { Terminal, Cpu, Settings, Play, RefreshCw, Sliders } from 'lucide-react';

interface Step3Props {
  logs: LogEntry[];
}

const Step3Log: React.FC<Step3Props> = ({ logs: initialLogs }) => {
  const [internalLogs, setInternalLogs] = useState<LogEntry[]>(initialLogs);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Strategy Parameters State
  const [params, setParams] = useState({
    upperThreshold: 0.20,
    lowerThreshold: 0.21,
    minDuration: 2.0,
    maxDuration: 6.0,
    mergeGap: 1.0
  });

  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);

  // Auto-scroll logs
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [internalLogs]);

  const handleRunStrategy = () => {
    if (isProcessing) return;
    setIsProcessing(true);
    setProgress(0);
    setInternalLogs([]); // Clear logs for new run

    // Simulate process
    let step = 0;
    const interval = setInterval(() => {
      setProgress(prev => Math.min(prev + 2, 100));
      step++;

      // Inject logs based on progress steps
      if (step === 5) addLog('info', `Initializing serialization with Threshold=[${params.lowerThreshold}, ${params.upperThreshold}]`);
      if (step === 15) addLog('info', `Loaded 7 video contexts into memory.`);
      if (step === 25) addLog('filter', `Filtering segments < ${params.minDuration}s...`);
      if (step === 35) addLog('filter', `Dropped 12 noise segments (Score < ${params.lowerThreshold})`);
      if (step === 50) addLog('merge', `Analyzing gaps < ${params.mergeGap}s for merge candidates...`);
      if (step === 65) addLog('merge', `Merged Seg#12 and Seg#13 (Gap: 0.2s)`);
      if (step === 80) addLog('merge', `Merged Seg#45 and Seg#46 (Gap: 0.5s)`);
      if (step === 95) addLog('result', `Serialization Complete. 8 Final Cuts generated.`);

      if (step >= 50 && step < 90 && step % 10 === 0) {
           // Random noise logs
           addLog('info', `Processing batch chunk #${step}...`);
      }

      if (step >= 100) {
        clearInterval(interval);
        setIsProcessing(false);
        setProgress(100);
      }
    }, 30);
  };

  const addLog = (type: LogEntry['type'], message: string) => {
    const newLog: LogEntry = {
      id: Date.now().toString() + Math.random(),
      type,
      message,
      timestamp: new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
    };
    setInternalLogs(prev => [...prev, newLog]);
  };

  const handleChange = (key: keyof typeof params, value: string) => {
    setParams(prev => ({ ...prev, [key]: parseFloat(value) }));
  };

  return (
    <section className="mb-12 border-b border-slate-800 pb-12 snap-start scroll-mt-6">
      <div className="flex items-center gap-3 mb-6 px-6">
        <div className="w-8 h-8 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-sm">03</div>
        <h2 className="text-xl font-bold text-slate-100">Strategy Blackbox</h2>
        <span className="text-xs text-slate-500 uppercase tracking-wide border border-slate-700 px-2 py-0.5 rounded">Logic & Serialization</span>
      </div>

      <div className="px-6 grid grid-cols-10 gap-6 h-[450px]">
        
        {/* LEFT COLUMN: Parameters (30%) */}
        <div className="col-span-3 bg-slate-900 rounded-lg border border-slate-800 p-5 flex flex-col shadow-lg">
           <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-5 pb-2 border-b border-slate-800/50">
              <Settings size={14} /> Configuration
           </div>
           
           <div className="flex-1 space-y-4 overflow-y-auto pr-1 custom-scrollbar">
              
              <div className="grid grid-cols-2 gap-4">
                 <div className="space-y-1">
                    <label className="text-[10px] text-slate-500 font-bold uppercase">Upper Threshold</label>
                    <input 
                       type="number" step="0.01"
                       value={params.upperThreshold}
                       onChange={(e) => handleChange('upperThreshold', e.target.value)}
                       className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:border-cyan-500 outline-none transition-colors font-mono"
                    />
                 </div>
                 <div className="space-y-1">
                    <label className="text-[10px] text-slate-500 font-bold uppercase">Lower Threshold</label>
                    <input 
                       type="number" step="0.01"
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
                       type="number" step="0.1"
                       value={params.minDuration}
                       onChange={(e) => handleChange('minDuration', e.target.value)}
                       className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:border-cyan-500 outline-none transition-colors font-mono"
                  />
              </div>

               <div className="space-y-1">
                  <label className="text-[10px] text-slate-500 font-bold uppercase">Max Duration (s)</label>
                  <input 
                       type="number" step="0.1"
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
                       type="number" step="0.1"
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
                     className="w-full bg-amber-600/20 hover:bg-amber-600/30 text-amber-500 border border-amber-600/50 hover:border-amber-500 py-2 rounded text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2"
                   >
                     <Play size={12} fill="currentColor" /> Run Strategy
                   </button>
               )}
           </div>
        </div>

        {/* RIGHT COLUMN: Log Console (70%) */}
        <div className="col-span-7 bg-black rounded-lg border border-slate-800 p-4 font-mono text-xs shadow-inner flex flex-col relative overflow-hidden">
           
           {/* Terminal Header */}
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
           
           {/* Log Content */}
           <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-1.5 pr-2 custom-scrollbar relative z-10">
             {internalLogs.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center opacity-20 pointer-events-none">
                    <span className="text-4xl font-bold text-slate-700">NO LOGS</span>
                </div>
             )}
             {internalLogs.map((log) => {
               let colorClass = 'text-slate-300';
               let bgClass = '';
               
               if (log.type === 'filter') { colorClass = 'text-rose-400'; bgClass = 'bg-rose-950/10'; }
               if (log.type === 'merge') { colorClass = 'text-cyan-400'; bgClass = 'bg-cyan-950/10'; }
               if (log.type === 'result') { colorClass = 'text-emerald-400 font-bold'; bgClass = 'bg-emerald-950/20 border-l-2 border-emerald-500 pl-2'; }
               if (log.type === 'info') { colorClass = 'text-slate-400'; }

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

           {/* Scanline Effect */}
           <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] z-[5] bg-[length:100%_2px,3px_100%] pointer-events-none opacity-20"></div>
        </div>

      </div>
    </section>
  );
};

export default Step3Log;
