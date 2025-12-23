import React, { useEffect, useMemo, useState } from 'react';
import { ThemeSummary } from '../types';
import { Play, Activity, ChevronDown } from 'lucide-react';
import { useLogStore } from '../context/LogContext';

interface Step3Props {
  themes: ThemeSummary[];
  activeThemeSlug: string | null;
  onSelectTheme: (theme: ThemeSummary) => void;
  onSequenceComplete?: () => void;
  isLoadingThemes?: boolean;
  themesError?: string | null;
}

const DEFAULT_PARAMS = {
  upperThreshold: 0.2,
  lowerThreshold: 0.15,
  minDuration: 2.0,
  maxDuration: 6.0,
  mergeGap: 1.0,
};

const Step3Log: React.FC<Step3Props> = ({
  themes,
  activeThemeSlug,
  onSelectTheme,
  onSequenceComplete,
  isLoadingThemes,
  themesError,
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const apiBase = import.meta.env.VITE_API_BASE || '';
  const resolveApiPath = (path: string) => (apiBase ? `${apiBase}${path}` : path);
  const { lastEvent } = useLogStore();

  const selectedTheme = useMemo(() => {
    return themes.find((theme) => theme.theme_slug === activeThemeSlug) || null;
  }, [themes, activeThemeSlug]);

  useEffect(() => {
    setStatusMessage(null);
    setProgress(0);
    setIsProcessing(false);
  }, [selectedTheme?.theme_slug]);

  useEffect(() => {
    if (!lastEvent || lastEvent.stage !== 'sequence') {
      return;
    }
    if (selectedTheme) {
      if (lastEvent.theme_slug && lastEvent.theme_slug !== selectedTheme.theme_slug) {
        return;
      }
      if (!lastEvent.theme_slug && lastEvent.theme && lastEvent.theme !== selectedTheme.theme) {
        return;
      }
    }
    const status = lastEvent.status as string | undefined;
    if (status === 'queued' || status === 'running') {
      setIsProcessing(true);
    }
    if (status === 'done' || status === 'cached' || status === 'error') {
      setIsProcessing(false);
      setProgress(100);
      if (status === 'done' || status === 'cached') {
        onSequenceComplete?.();
      }
    }
    if (typeof lastEvent.progress === 'number') {
      setProgress(Math.round(lastEvent.progress * 100));
    }
    if (typeof lastEvent.message === 'string' && lastEvent.message) {
      setStatusMessage(lastEvent.message);
    }
  }, [lastEvent, selectedTheme, onSequenceComplete]);

  const handleRunStrategy = async () => {
    if (isProcessing) {
      return;
    }
    if (!selectedTheme) {
      setStatusMessage('Please select a theme first.');
      return;
    }
    setStatusMessage(null);
    setIsProcessing(true);
    setProgress(0);
    try {
      const response = await fetch(resolveApiPath('/api/sequence'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          theme: selectedTheme.theme,
          theme_slug: selectedTheme.theme_slug,
          params: {
            upper_threshold: DEFAULT_PARAMS.upperThreshold,
            lower_threshold: DEFAULT_PARAMS.lowerThreshold,
            min_duration: DEFAULT_PARAMS.minDuration,
            max_duration: DEFAULT_PARAMS.maxDuration,
            merge_gap: DEFAULT_PARAMS.mergeGap,
          },
          force: false,
          video_ids: selectedTheme.video_ids,
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
      setStatusMessage(error instanceof Error ? error.message : 'Sequence failed');
    }
  };

  return (
    <section className="mb-12 border-b border-slate-800 pb-10 snap-start scroll-mt-6">
      <div className="flex items-center justify-between mb-6 px-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-sm">03</div>
          <h2 className="text-xl font-bold text-slate-100">Strategy Blackbox</h2>
          <span className="text-xs text-slate-500 uppercase tracking-wide border border-slate-700 px-2 py-0.5 rounded">Sequencing</span>
        </div>
        {statusMessage && (
          <span className="text-xs text-rose-400">{statusMessage}</span>
        )}
      </div>

      <div className="px-6 grid grid-cols-12 gap-6">
        <div className="col-span-5 bg-slate-900 rounded-lg border border-slate-800 p-5 shadow-lg">
          <div className="text-[11px] text-slate-500 uppercase tracking-wider font-bold mb-3">Theme Selection</div>
          <div className="relative">
            <select
              value={selectedTheme?.theme_slug || ''}
              onChange={(event) => {
                const theme = themes.find((item) => item.theme_slug === event.target.value);
                if (theme) {
                  onSelectTheme(theme);
                }
              }}
              className="w-full bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-md pl-3 pr-10 py-2 appearance-none focus:outline-none focus:border-cyan-500"
            >
              <option value="">Select Theme</option>
              {themes.map((item) => (
                <option key={item.theme_slug} value={item.theme_slug}>
                  {item.theme}
                </option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          </div>

          <div className="mt-4 text-[10px] text-slate-500 space-y-1">
            {isLoadingThemes && <div>Loading themes...</div>}
            {themesError && <div className="text-rose-400">{themesError}</div>}
            {!isLoadingThemes && themes.length === 0 && (
              <div>No theme results yet. Run Stage 2 first.</div>
            )}
            {selectedTheme && (
              <div className="space-y-1">
                <div>Slug: <span className="font-mono text-slate-300">{selectedTheme.theme_slug}</span></div>
                <div>Videos: <span className="font-mono text-slate-300">{selectedTheme.video_ids.length}</span></div>
                <div>EDL: <span className="font-mono text-slate-300">{selectedTheme.has_edl ? 'Ready' : 'Pending'}</span></div>
              </div>
            )}
          </div>
        </div>

        <div className="col-span-7 bg-slate-950 rounded-lg border border-slate-800 p-6 flex flex-col justify-between">
          <div>
            <div className="text-[11px] text-slate-500 uppercase tracking-wider font-bold mb-2">Sequencing Control</div>
            <p className="text-xs text-slate-400 leading-relaxed">
              This stage stitches the highest-scoring clips into a single edit decision list. Advanced strategy controls will be added later.
            </p>
          </div>

          <div className="mt-6 space-y-3">
            <div className="flex items-center justify-between text-[10px] text-slate-400">
              <span>Status</span>
              <span>{isProcessing ? 'Running' : selectedTheme?.has_edl ? 'EDL Ready' : 'Idle'}</span>
            </div>
            <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-150 ${isProcessing ? 'bg-amber-500' : 'bg-emerald-500'}`}
                style={{ width: `${Math.min(progress, 100)}%` }}
              />
            </div>
            <button
              onClick={handleRunStrategy}
              disabled={!selectedTheme || isProcessing}
              className={`w-full py-2 rounded text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
                !selectedTheme || isProcessing
                  ? 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
                  : 'bg-amber-600/20 hover:bg-amber-600/30 text-amber-500 border border-amber-600/50 hover:border-amber-500'
              }`}
            >
              {isProcessing ? <Activity size={12} className="animate-spin" /> : <Play size={12} fill="currentColor" />}
              {isProcessing ? 'Sequencing...' : 'Run Sequencer'}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Step3Log;
