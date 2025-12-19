
import React, { useState, useEffect } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { RefreshCw, Tag, GitBranch } from 'lucide-react';
import { generateClusterPoints } from '../constants';
import { ClusterPoint } from '../types';

interface ClusterSandboxProps {
  // Converted to full page, no props needed for open/close state
}

const COLORS = ['#06b6d4', '#10b981', '#f43f5e', '#8b5cf6'];

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload as ClusterPoint;
    return (
      <div className="bg-slate-900 border border-slate-700 p-2 rounded shadow-xl z-50">
        <div className="w-32 aspect-video bg-black mb-1 rounded overflow-hidden">
           <img src={data.thumbnail} alt="Cluster Point" className="w-full h-full object-cover" />
        </div>
        <p className="text-[10px] text-slate-400 font-mono">ID: {data.id}</p>
        <p className="text-[10px] text-white">Cluster: Group {data.clusterId}</p>
      </div>
    );
  }
  return null;
};

const ClusterSandbox: React.FC<ClusterSandboxProps> = () => {
  const [data, setData] = useState<ClusterPoint[]>([]);
  const [kValue, setKValue] = useState(3);

  useEffect(() => {
    setData(generateClusterPoints(50));
  }, []);

  const handleRun = () => {
    setData(generateClusterPoints(50)); // Reshuffle for demo
  };

  return (
    <div className="w-full h-full flex flex-col animate-in fade-in duration-500">
      
      {/* Page Content */}
      <div className="flex flex-1 overflow-hidden bg-slate-950 rounded-xl border border-slate-800/50 m-6 shadow-2xl relative">
         
         {/* Controls Sidebar */}
         <div className="w-72 bg-slate-900/50 border-r border-slate-800 p-6 flex flex-col gap-6 backdrop-blur-sm z-10">
            <div className="mb-2">
                <div className="flex items-center gap-2 mb-1">
                    <GitBranch className="text-purple-400" size={18} />
                    <h3 className="font-bold text-slate-200">Unsupervised Labs</h3>
                </div>
                <p className="text-xs text-slate-500">Explore latent embedding spaces to discover hidden patterns in your footage.</p>
            </div>
            
            <hr className="border-slate-800/50" />

            <div>
              <label className="text-xs font-bold text-slate-400 uppercase mb-2 block">Algorithm</label>
              <select className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2.5 focus:ring-1 focus:ring-purple-500 outline-none transition-all">
                <option>K-Means Clustering</option>
                <option>DBSCAN</option>
                <option>Spectral Clustering</option>
              </select>
            </div>
            
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase mb-3 block flex justify-between">
                <span>K-Value (Clusters)</span>
                <span className="text-cyan-400 bg-cyan-950/30 px-2 rounded">{kValue}</span>
              </label>
              <input 
                type="range" min="2" max="10" 
                value={kValue}
                onChange={(e) => setKValue(parseInt(e.target.value))}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
              />
              <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono">
                <span>Coarse</span>
                <span>Fine</span>
              </div>
            </div>

            <div className="mt-auto space-y-3">
               <button 
                 onClick={handleRun}
                 className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-purple-900/20 active:scale-[0.98]"
               >
                 <RefreshCw size={18} /> Run Analysis
               </button>
               <p className="text-[10px] text-slate-600 text-center">Estimated runtime: ~1.2s</p>
            </div>
         </div>

         {/* Visualization Area */}
         <div className="flex-1 flex flex-col bg-[#0b0c15] relative">
            <div className="absolute top-6 left-6 z-10 pointer-events-none">
                <div className="text-xs font-mono text-slate-500 mb-1">PROJECTION METHOD</div>
                <div className="text-2xl font-bold text-slate-300 tracking-tight">t-SNE Manifold</div>
            </div>
            
            <div className="flex-1 p-6">
                <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 40, right: 40, bottom: 40, left: 40 }}>
                    <XAxis type="number" dataKey="x" name="dimension_1" hide />
                    <YAxis type="number" dataKey="y" name="dimension_2" hide />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} content={<CustomTooltip />} />
                    <Scatter name="Segments" data={data} fill="#8884d8" animationDuration={1000}>
                        {data.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[entry.clusterId % COLORS.length]} />
                        ))}
                    </Scatter>
                    </ScatterChart>
                </ResponsiveContainer>
            </div>
         </div>

         {/* Right Sidebar: Latent Labels */}
         <div className="w-80 border-l border-slate-800 bg-slate-900/30 p-6 overflow-y-auto">
            <div className="flex items-center gap-2 mb-4">
                 <Tag size={16} className="text-cyan-500" />
                 <h3 className="text-xs font-bold text-slate-300 uppercase">Discovered Topics</h3>
            </div>
            
            <div className="space-y-4">
               {[...Array(kValue)].map((_, i) => (
                 <div key={i} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50 hover:border-purple-500/50 transition-colors group">
                    <div className="flex items-center gap-3 mb-2">
                       <div className="w-3 h-3 rounded-full shadow-[0_0_8px_currentColor]" style={{ backgroundColor: COLORS[i % COLORS.length], color: COLORS[i % COLORS.length] }} />
                       <span className="text-sm font-semibold text-slate-200">Cluster {i + 1}</span>
                       <span className="ml-auto text-[10px] text-slate-500 font-mono bg-slate-900 px-1.5 py-0.5 rounded">{Math.floor(Math.random() * 30 + 10)}%</span>
                    </div>
                    
                    <div className="aspect-video bg-black rounded mb-2 overflow-hidden relative border border-slate-800 group-hover:border-slate-600 transition-colors">
                       <img src={`https://picsum.photos/200/120?random=${i + 100}`} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                       <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black to-transparent p-2">
                          <p className="text-[9px] text-slate-300 font-mono">Centroid: seg_{Math.floor(Math.random() * 100)}</p>
                       </div>
                    </div>
                    
                    <div className="text-xs text-purple-200 bg-purple-900/10 p-2 rounded border border-purple-500/10 flex items-center gap-2">
                       <div className="w-1 h-3 bg-purple-500 rounded-full"></div>
                       Latent Label: "Topic {i+1}"
                    </div>
                 </div>
               ))}
            </div>
         </div>
      </div>
    </div>
  );
};

export default ClusterSandbox;
