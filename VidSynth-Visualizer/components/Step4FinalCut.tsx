
import React from 'react';
import { VideoResource } from '../types';
import { Clapperboard, Download, Scissors } from 'lucide-react';

interface Step4Props {
  video: VideoResource;
}

const Step4FinalCut: React.FC<Step4Props> = ({ video }) => {
  return (
    <section className="mb-24 px-6 snap-start scroll-mt-6">
       <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-sm">04</div>
            <h2 className="text-xl font-bold text-slate-100">Final Cut</h2>
        </div>
        <button className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 shadow-lg shadow-indigo-500/20 transition-all">
          <Download size={16} /> Export Video
        </button>
      </div>

      <div className="flex flex-col xl:flex-row gap-6 h-[500px]">
         {/* Main Final Player */}
         <div className="flex-1 bg-black rounded-xl border border-slate-800 shadow-2xl relative overflow-hidden group">
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <span className="text-slate-700 font-mono text-sm tracking-widest uppercase">Composite Preview</span>
            </div>
            {/* Placeholder for composited video */}
            <video className="w-full h-full object-contain opacity-50" src={video.url} muted />
            
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-slate-900/80 backdrop-blur rounded-full px-6 py-2 border border-white/10 flex items-center gap-4">
               <button className="text-white hover:text-cyan-400"><Scissors size={18} /></button>
               <div className="w-64 h-1 bg-slate-600 rounded-full overflow-hidden">
                 <div className="w-1/2 h-full bg-indigo-500" />
               </div>
               <span className="text-xs font-mono text-white">00:42 / 01:15</span>
            </div>
         </div>

         {/* EDL List */}
         <div className="w-full xl:w-96 bg-slate-900 rounded-xl border border-slate-800 flex flex-col overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-slate-950/30 flex justify-between items-center">
               <h3 className="text-sm font-bold text-slate-300 flex items-center gap-2">
                 <Clapperboard size={14} /> EDL (Edit Decision List)
               </h3>
               <span className="text-[10px] text-slate-500">8 Segments</span>
            </div>
            
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
               {/* Mock EDL Items */}
               {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                 <div key={i} className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer group">
                    <span className="text-xs font-mono text-slate-600 w-4">{i.toString().padStart(2, '0')}</span>
                    <div className="w-12 h-8 bg-slate-700 rounded overflow-hidden">
                       <img src={`https://picsum.photos/100/60?random=${i + 50}`} className="w-full h-full object-cover" />
                    </div>
                    <div className="flex flex-col">
                       <span className="text-xs font-mono text-slate-300">00:1{i}.00 -&gt; 00:1{i + 3}.00</span>
                       <span className="text-[10px] text-slate-500">Source: {video.name}</span>
                    </div>
                 </div>
               ))}
            </div>
            
            <div className="p-3 border-t border-slate-800 bg-slate-950/30 text-center">
              <span className="text-[10px] text-slate-500 font-mono">Total Duration: 42s</span>
            </div>
         </div>
      </div>
    </section>
  );
};

export default Step4FinalCut;
