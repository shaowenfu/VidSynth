import React, { useEffect, useMemo, useState } from 'react';
import { Sliders, X, RefreshCw } from 'lucide-react';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

type SettingsValue = string | number | boolean | null;

interface SettingsBundle {
  settings: Record<string, any>;
  override: Record<string, any>;
  has_secrets?: Record<string, boolean>;
  paths?: {
    baseline?: string;
    override?: string;
    active?: string;
  };
  applied?: boolean;
}

interface FieldHelp {
  definition: string;
  impact: string;
  example: string;
}

type FieldType = 'text' | 'number' | 'boolean' | 'select' | 'textarea' | 'secret';

interface FieldSpec {
  path: string[];
  label: string;
  type: FieldType;
  step?: number;
  placeholder?: string;
  unit?: string;
  options?: Array<{ label: string; value: string }>;
  help: FieldHelp;
}

interface SectionSpec {
  id: string;
  title: string;
  description: string;
  fields: FieldSpec[];
  span?: 1 | 2;
}

const SECRET_PATHS = new Set(['llm.api_key', 'llm.openai_api_key', 'llm.deepseek_api_key']);

const isObject = (value: any) => value && typeof value === 'object' && !Array.isArray(value);

const deepEqual = (left: any, right: any): boolean => {
  if (left === right) return true;
  if (!isObject(left) || !isObject(right)) return false;
  const leftKeys = Object.keys(left);
  const rightKeys = Object.keys(right);
  if (leftKeys.length !== rightKeys.length) return false;
  return leftKeys.every((key) => deepEqual(left[key], right[key]));
};

const getNestedValue = (target: Record<string, any>, path: string[]): SettingsValue => {
  return path.reduce((acc, key) => (acc && acc[key] !== undefined ? acc[key] : undefined), target);
};

const setNestedValue = (target: Record<string, any>, path: string[], value: SettingsValue) => {
  const next = JSON.parse(JSON.stringify(target)) as Record<string, any>;
  let cursor = next;
  for (let i = 0; i < path.length - 1; i += 1) {
    const key = path[i];
    if (!cursor[key] || typeof cursor[key] !== 'object') {
      cursor[key] = {};
    }
    cursor = cursor[key];
  }
  cursor[path[path.length - 1]] = value;
  return next;
};

const diffSettings = (base: any, updated: any, path: string[] = []): any => {
  const pathKey = path.join('.');
  if (SECRET_PATHS.has(pathKey)) {
    return undefined;
  }
  if (!isObject(base) || !isObject(updated)) {
    if (Object.is(base, updated)) {
      return undefined;
    }
    return updated;
  }
  const result: Record<string, any> = {};
  const keys = new Set([...Object.keys(base), ...Object.keys(updated)]);
  keys.forEach((key) => {
    const child = diffSettings(base[key], updated[key], [...path, key]);
    if (child !== undefined) {
      result[key] = child;
    }
  });
  return Object.keys(result).length > 0 ? result : undefined;
};

const tooltipCopy = (help: FieldHelp) => (
  <div className="space-y-2 text-[11px] leading-relaxed text-slate-200">
    <div>
      <div className="text-[10px] uppercase tracking-wider text-slate-400">Definition</div>
      <div>{help.definition}</div>
    </div>
    <div>
      <div className="text-[10px] uppercase tracking-wider text-slate-400">Impact</div>
      <div>{help.impact}</div>
    </div>
    <div>
      <div className="text-[10px] uppercase tracking-wider text-slate-400">Example</div>
      <div>{help.example}</div>
    </div>
  </div>
);

const SECTIONS: SectionSpec[] = [
  {
    id: 'segment',
    title: 'Segmentation',
    description: 'Controls how the raw video is split into clips.',
    fields: [
      {
        path: ['segment', 'fps_keyframe'],
        label: 'fps_keyframe',
        type: 'number',
        step: 0.1,
        unit: 'fps',
        help: {
          definition: 'Keyframe sampling rate used during segmentation.',
          impact: 'Higher values detect finer cuts but cost more compute. Lower values are faster but may miss fast transitions.',
          example: 'Example: 1.0 samples one frame per second.',
        },
      },
      {
        path: ['segment', 'cosine_threshold'],
        label: 'cosine_threshold',
        type: 'number',
        step: 0.01,
        help: {
          definition: 'Cosine distance threshold for embedding change between frames.',
          impact: 'Lower values trigger more cuts. Higher values merge more content into a single clip.',
          example: 'Example: 0.3 is a balanced starting point.',
        },
      },
      {
        path: ['segment', 'histogram_threshold'],
        label: 'histogram_threshold',
        type: 'number',
        step: 0.01,
        help: {
          definition: 'HSV histogram distance threshold for visual changes.',
          impact: 'Lower values split on subtle color shifts. Higher values ignore minor lighting changes.',
          example: 'Example: 0.45 detects hard cuts without over-splitting.',
        },
      },
      {
        path: ['segment', 'min_clip_seconds'],
        label: 'min_clip_seconds',
        type: 'number',
        step: 0.1,
        unit: 's',
        help: {
          definition: 'Minimum duration for a valid clip in segmentation.',
          impact: 'Shorter limits keep rapid cuts; higher values merge or drop tiny clips.',
          example: 'Example: 1.0 keeps fast motion clips.',
        },
      },
      {
        path: ['segment', 'max_clip_seconds'],
        label: 'max_clip_seconds',
        type: 'number',
        step: 0.1,
        unit: 's',
        help: {
          definition: 'Maximum duration for a clip before forced splitting.',
          impact: 'Lower values keep clips short and punchy. Higher values allow long continuous shots.',
          example: 'Example: 6.0 keeps clips under 6 seconds.',
        },
      },
      {
        path: ['segment', 'merge_short_segments'],
        label: 'merge_short_segments',
        type: 'boolean',
        help: {
          definition: 'Whether to merge segments shorter than the minimum duration.',
          impact: 'On keeps the timeline smooth; off may produce many tiny clips.',
          example: 'Example: true merges short flashes into nearby clips.',
        },
      },
      {
        path: ['segment', 'keep_last_short_segment'],
        label: 'keep_last_short_segment',
        type: 'boolean',
        help: {
          definition: 'Whether to keep the last short segment at the end of a video.',
          impact: 'On preserves the ending even if short; off may drop endings.',
          example: 'Example: true keeps a brief outro clip.',
        },
      },
      {
        path: ['segment', 'split_long_segments'],
        label: 'split_long_segments',
        type: 'boolean',
        help: {
          definition: 'Whether to split clips that exceed the maximum duration.',
          impact: 'On enforces uniform clip length; off keeps long shots intact.',
          example: 'Example: true keeps the clip list consistent for sequencing.',
        },
      },
    ],
  },
  {
    id: 'theme_match',
    title: 'Theme Matching',
    description: 'Controls scoring logic for visual-semantic similarity.',
    fields: [
      {
        path: ['theme_match', 'score_threshold'],
        label: 'score_threshold',
        type: 'number',
        step: 0.01,
        help: {
          definition: 'Minimum score to consider a clip relevant to the theme.',
          impact: 'Higher values produce fewer, higher-confidence clips. Lower values increase recall.',
          example: 'Example: 0.1 keeps more candidates for sequencing.',
        },
      },
      {
        path: ['theme_match', 'negative_weight'],
        label: 'negative_weight',
        type: 'number',
        step: 0.05,
        help: {
          definition: 'Penalty applied to negative prompts during scoring.',
          impact: 'Higher values punish negatives more aggressively, reducing false positives.',
          example: 'Example: 0.8 strongly downweights off-theme scenes.',
        },
      },
    ],
  },
  {
    id: 'embedding',
    title: 'Embedding',
    description: 'Controls the visual embedding backend and hardware usage.',
    fields: [
      {
        path: ['embedding', 'backend'],
        label: 'backend',
        type: 'select',
        options: [
          { label: 'mean_color', value: 'mean_color' },
          { label: 'open_clip', value: 'open_clip' },
        ],
        help: {
          definition: 'Embedding backend used to encode frames into vectors.',
          impact: 'mean_color is fast but non-semantic. open_clip is semantic but heavier.',
          example: 'Example: open_clip enables theme matching beyond color.',
        },
      },
      {
        path: ['embedding', 'preset'],
        label: 'preset',
        type: 'select',
        options: [
          { label: 'cpu-small', value: 'cpu-small' },
          { label: 'gpu-large', value: 'gpu-large' },
        ],
        help: {
          definition: 'Preset controlling model size and performance.',
          impact: 'cpu-small runs on CPU quickly; gpu-large is slower but more accurate.',
          example: 'Example: cpu-small for laptops, gpu-large for dedicated GPUs.',
        },
      },
      {
        path: ['embedding', 'model_name'],
        label: 'model_name',
        type: 'text',
        help: {
          definition: 'Model name for the embedding backend.',
          impact: 'Changing model_name affects feature space and scoring quality.',
          example: 'Example: ViT-B-32 is a balanced default.',
        },
      },
      {
        path: ['embedding', 'pretrained'],
        label: 'pretrained',
        type: 'text',
        help: {
          definition: 'Pretrained weight tag for the embedding model.',
          impact: 'Different pretrained checkpoints vary in domain coverage.',
          example: 'Example: laion400m_e32 is a common default.',
        },
      },
      {
        path: ['embedding', 'device'],
        label: 'device',
        type: 'text',
        placeholder: 'cpu / cuda / cuda:0',
        help: {
          definition: 'Device string used by the embedding runtime.',
          impact: 'cpu is stable but slower. cuda targets GPU acceleration.',
          example: 'Example: cuda:0 selects the first GPU.',
        },
      },
      {
        path: ['embedding', 'precision'],
        label: 'precision',
        type: 'select',
        options: [
          { label: 'fp32', value: 'fp32' },
          { label: 'amp', value: 'amp' },
        ],
        help: {
          definition: 'Numeric precision used in the embedding runtime.',
          impact: 'amp speeds up GPU inference but may reduce precision slightly.',
          example: 'Example: fp32 for deterministic results on CPU.',
        },
      },
    ],
  },
  {
    id: 'sequence',
    title: 'Sequencing',
    description: 'Controls how clips are filtered and merged into an EDL.',
    fields: [
      {
        path: ['sequence', 'threshold_upper'],
        label: 'threshold_upper',
        type: 'number',
        step: 0.01,
        help: {
          definition: 'Score threshold to start a selection streak.',
          impact: 'Higher values favor only the strongest clips.',
          example: 'Example: 0.2 starts only on high-confidence segments.',
        },
      },
      {
        path: ['sequence', 'threshold_lower'],
        label: 'threshold_lower',
        type: 'number',
        step: 0.01,
        help: {
          definition: 'Score threshold to continue a selection streak.',
          impact: 'Lower values allow smoother continuity; higher values cut aggressively.',
          example: 'Example: 0.15 keeps momentum after a strong start.',
        },
      },
      {
        path: ['sequence', 'min_duration'],
        label: 'min_duration',
        type: 'number',
        step: 0.1,
        unit: 's',
        help: {
          definition: 'Minimum clip duration allowed in the final EDL.',
          impact: 'Shorter values keep quick cuts; higher values enforce longer clips.',
          example: 'Example: 2.0 keeps sequences from being too jittery.',
        },
      },
      {
        path: ['sequence', 'max_duration'],
        label: 'max_duration',
        type: 'number',
        step: 0.1,
        unit: 's',
        help: {
          definition: 'Maximum clip duration allowed in the final EDL.',
          impact: 'Lower values keep a fast rhythm; higher values allow longer scenes.',
          example: 'Example: 6.0 keeps scenes compact and punchy.',
        },
      },
      {
        path: ['sequence', 'merge_gap'],
        label: 'merge_gap',
        type: 'number',
        step: 0.1,
        unit: 's',
        help: {
          definition: 'Maximum gap between clips to merge into a continuous segment.',
          impact: 'Higher values merge across short gaps; lower values keep strict boundaries.',
          example: 'Example: 1.0 merges clips with up to 1 second gap.',
        },
      },
    ],
  },
  {
    id: 'export',
    title: 'Export',
    description: 'Controls rendering and output encoding.',
    fields: [
      {
        path: ['export', 'video_codec'],
        label: 'video_codec',
        type: 'text',
        help: {
          definition: 'Video codec used for final rendering.',
          impact: 'Codec controls compatibility and quality.',
          example: 'Example: libx264 is widely supported.',
        },
      },
      {
        path: ['export', 'video_bitrate'],
        label: 'video_bitrate',
        type: 'text',
        help: {
          definition: 'Target video bitrate.',
          impact: 'Higher bitrate improves quality but increases file size.',
          example: 'Example: 8M is a good balance for previews.',
        },
      },
      {
        path: ['export', 'audio_fade_ms'],
        label: 'audio_fade_ms',
        type: 'number',
        step: 10,
        unit: 'ms',
        help: {
          definition: 'Audio fade-in/out duration per clip.',
          impact: 'Longer fades reduce harsh cuts but can soften short clips.',
          example: 'Example: 150 smooths transitions without muting.',
        },
      },
      {
        path: ['export', 'video_crossfade_ms'],
        label: 'video_crossfade_ms',
        type: 'number',
        step: 10,
        unit: 'ms',
        help: {
          definition: 'Video crossfade duration per clip boundary.',
          impact: 'Longer crossfades look smoother but may blur fast cuts.',
          example: 'Example: 200 adds a subtle transition.',
        },
      },
    ],
  },
  {
    id: 'cluster',
    title: 'Clustering',
    description: 'Controls summary clustering for sandbox analysis.',
    fields: [
      {
        path: ['cluster', 'max_clusters'],
        label: 'max_clusters',
        type: 'number',
        step: 1,
        help: {
          definition: 'Maximum number of clusters to generate.',
          impact: 'Higher values produce more granular grouping.',
          example: 'Example: 20 clusters for a balanced overview.',
        },
      },
      {
        path: ['cluster', 'representative_count'],
        label: 'representative_count',
        type: 'number',
        step: 1,
        help: {
          definition: 'Number of representative clips per cluster.',
          impact: 'Higher values show more variety but increase processing.',
          example: 'Example: 5 representatives per cluster.',
        },
      },
    ],
  },
  {
    id: 'llm',
    title: 'LLM & Prompts',
    description: 'Controls theme expansion prompts and model connectivity.',
    span: 2,
    fields: [
      {
        path: ['llm', 'provider'],
        label: 'provider',
        type: 'select',
        options: [
          { label: 'deepseek', value: 'deepseek' },
          { label: 'openai', value: 'openai' },
        ],
        help: {
          definition: 'LLM provider used for theme expansion.',
          impact: 'Switching provider changes available models and pricing.',
          example: 'Example: deepseek for internal deployments.',
        },
      },
      {
        path: ['llm', 'base_url'],
        label: 'base_url',
        type: 'text',
        placeholder: 'https://api.example.com',
        help: {
          definition: 'Base URL for the LLM API endpoint.',
          impact: 'Custom base_url enables proxy or self-hosted gateways.',
          example: 'Example: https://api.deepseek.com/v1',
        },
      },
      {
        path: ['llm', 'model'],
        label: 'model',
        type: 'text',
        placeholder: 'model-name',
        help: {
          definition: 'Model name used by the LLM provider.',
          impact: 'Different models have different quality and latency.',
          example: 'Example: deepseek-chat or gpt-4o-mini.',
        },
      },
      {
        path: ['llm', 'api_key'],
        label: 'api_key',
        type: 'secret',
        help: {
          definition: 'Primary API key used for LLM requests.',
          impact: 'Required for authenticated access to hosted models.',
          example: 'Example: paste a key starting with sk-...',
        },
      },
      {
        path: ['llm', 'openai_api_key'],
        label: 'openai_api_key',
        type: 'secret',
        help: {
          definition: 'Optional OpenAI-specific API key override.',
          impact: 'Use when provider is openai or for multi-provider routing.',
          example: 'Example: key stored only in secrets.json.',
        },
      },
      {
        path: ['llm', 'deepseek_api_key'],
        label: 'deepseek_api_key',
        type: 'secret',
        help: {
          definition: 'Optional DeepSeek-specific API key override.',
          impact: 'Use when provider is deepseek or for multi-provider routing.',
          example: 'Example: key stored only in secrets.json.',
        },
      },
      {
        path: ['llm', 'temperature'],
        label: 'temperature',
        type: 'number',
        step: 0.1,
        help: {
          definition: 'Sampling temperature for LLM outputs.',
          impact: 'Higher values produce more variety; lower values are deterministic.',
          example: 'Example: 0.3 keeps prompts focused.',
        },
      },
      {
        path: ['llm', 'timeout_s'],
        label: 'timeout_s',
        type: 'number',
        step: 1,
        unit: 's',
        help: {
          definition: 'Timeout for LLM requests.',
          impact: 'Lower values fail fast; higher values wait for slow models.',
          example: 'Example: 60 seconds for stable responses.',
        },
      },
      {
        path: ['prompts', 'expand', 'template'],
        label: 'prompts.expand.template',
        type: 'textarea',
        help: {
          definition: 'Prompt template used to expand a theme into keywords.',
          impact: 'Better templates produce clearer short tags for matching.',
          example: 'Example: "Expand theme: {theme}" uses {theme} placeholder.',
        },
      },
      {
        path: ['prompts', 'expand', 'negative_hint'],
        label: 'prompts.expand.negative_hint',
        type: 'textarea',
        help: {
          definition: 'Hint appended to discourage verbose phrases.',
          impact: 'Helps keep outputs concise and matchable.',
          example: 'Example: "Avoid abstract or multi-word sentences."',
        },
      },
    ],
  },
];

const SettingsPanel: React.FC<SettingsPanelProps> = ({ isOpen, onClose }) => {
  const [bundle, setBundle] = useState<SettingsBundle | null>(null);
  const [draft, setDraft] = useState<Record<string, any> | null>(null);
  const [original, setOriginal] = useState<Record<string, any> | null>(null);
  const [secretDraft, setSecretDraft] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const apiBase = import.meta.env.VITE_API_BASE || '';

  const fetchSettings = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}/api/settings`);
      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }
      const payload = (await response.json()) as SettingsBundle;
      setBundle(payload);
      setDraft(payload.settings);
      setOriginal(payload.settings);
      setSecretDraft({});
      setStatusMessage(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchSettings();
    }
  }, [isOpen]);

  const hasPendingSecrets = useMemo(
    () => Object.values(secretDraft).some((value) => value.trim() !== ''),
    [secretDraft]
  );

  const isDirty = useMemo(() => {
    if (!draft || !original) return false;
    if (!deepEqual(draft, original)) return true;
    return hasPendingSecrets;
  }, [draft, original, hasPendingSecrets]);

  const handleSecretChange = (pathKey: string, value: string) => {
    setSecretDraft((prev) => ({ ...prev, [pathKey]: value }));
  };

  const handleValueChange = (path: string[], value: SettingsValue) => {
    if (!draft) return;
    setDraft(setNestedValue(draft, path, value));
  };

  const buildSecretsPatch = () => {
    const secrets: Record<string, any> = {};
    Object.entries(secretDraft).forEach(([pathKey, value]) => {
      if (!value.trim()) return;
      const segments = pathKey.split('.');
      let cursor = secrets;
      segments.forEach((segment, idx) => {
        if (idx === segments.length - 1) {
          cursor[segment] = value.trim();
        } else {
          cursor[segment] = cursor[segment] || {};
          cursor = cursor[segment];
        }
      });
    });
    return secrets;
  };

  const handleSave = async () => {
    if (!draft || !original) return;
    setIsSaving(true);
    setError(null);
    setStatusMessage(null);
    try {
      const settingsPatch = diffSettings(original, draft) || {};
      const secretsPatch = buildSecretsPatch();
      const response = await fetch(`${apiBase}/api/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          settings: settingsPatch,
          secrets: secretsPatch,
          apply: true,
        }),
      });
      if (!response.ok) {
        throw new Error(`Save failed: ${response.status}`);
      }
      const payload = (await response.json()) as SettingsBundle;
      setBundle(payload);
      setDraft(payload.settings);
      setOriginal(payload.settings);
      setSecretDraft({});
      setStatusMessage('Settings applied.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Reset overrides and clear secrets?')) {
      return;
    }
    setIsSaving(true);
    setError(null);
    setStatusMessage(null);
    try {
      const response = await fetch(`${apiBase}/api/settings/reset`, { method: 'POST' });
      if (!response.ok) {
        throw new Error(`Reset failed: ${response.status}`);
      }
      const payload = (await response.json()) as SettingsBundle;
      setBundle(payload);
      setDraft(payload.settings);
      setOriginal(payload.settings);
      setSecretDraft({});
      setStatusMessage('Overrides reset.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed');
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-950 w-[980px] max-h-[85vh] rounded-2xl border border-slate-700 shadow-2xl flex flex-col overflow-hidden relative animate-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Sliders className="text-sky-400" size={18} />
            Settings Panel
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400 hover:text-white">
            <X size={20} />
          </button>
        </div>

        <div className="flex items-center justify-between px-6 py-3 border-b border-slate-800 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="uppercase tracking-wider">Runtime Settings</span>
            {statusMessage && <span className="text-emerald-400">{statusMessage}</span>}
            {error && <span className="text-rose-400">{error}</span>}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchSettings}
              className="flex items-center gap-1 text-[11px] bg-slate-900 hover:bg-slate-800 text-slate-300 px-3 py-1.5 rounded border border-slate-700"
              disabled={isLoading}
            >
              <RefreshCw size={12} /> Reload
            </button>
            <button
              onClick={handleReset}
              className="text-[11px] bg-rose-950/40 hover:bg-rose-900/40 text-rose-300 px-3 py-1.5 rounded border border-rose-900/60"
              disabled={isSaving}
            >
              Reset Overrides
            </button>
            <button
              onClick={handleSave}
              disabled={!isDirty || isSaving}
              className="text-[11px] bg-sky-600 hover:bg-sky-500 text-white px-4 py-1.5 rounded border border-sky-500/50 disabled:opacity-40"
            >
              {isSaving ? 'Saving...' : 'Save & Apply'}
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 custom-scrollbar space-y-6">
          {isLoading && (
            <div className="text-xs text-slate-500">Loading settings...</div>
          )}

          {draft && (
            <div className="grid grid-cols-2 gap-6">
              {SECTIONS.map((section) => (
                <section
                  key={section.id}
                  className={`bg-slate-900/40 border border-slate-800 rounded-xl p-4 space-y-4 ${
                    section.span === 2 ? 'col-span-2' : ''
                  }`}
                >
                  <div>
                    <div className="text-xs font-semibold text-slate-200">{section.title}</div>
                    <div className="text-[11px] text-slate-500">{section.description}</div>
                  </div>
                  <div className="space-y-4">
                    {section.fields.map((field) => {
                      const pathKey = field.path.join('.');
                      const value = getNestedValue(draft, field.path);
                      const hasSecret = bundle?.has_secrets?.[pathKey];
                      const inputValue = field.type === 'secret'
                        ? secretDraft[pathKey] ?? ''
                        : value ?? '';

                      const renderInput = () => {
                        switch (field.type) {
                          case 'boolean': {
                            const isOn = Boolean(value);
                            return (
                              <button
                                onClick={() => handleValueChange(field.path, !isOn)}
                                className={`w-14 h-7 rounded-full border transition-colors ${
                                  isOn
                                    ? 'bg-emerald-500/20 border-emerald-500/60'
                                    : 'bg-slate-900 border-slate-700'
                                }`}
                              >
                                <span
                                  className={`block w-5 h-5 rounded-full bg-white transition-transform ${
                                    isOn ? 'translate-x-7' : 'translate-x-1'
                                  }`}
                                />
                              </button>
                            );
                          }
                          case 'select':
                            return (
                              <select
                                value={String(value ?? '')}
                                onChange={(event) => handleValueChange(field.path, event.target.value)}
                                className="w-full bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-md px-3 py-2 focus:outline-none focus:border-slate-500"
                              >
                                {field.options?.map((option) => (
                                  <option key={option.value} value={option.value}>
                                    {option.label}
                                  </option>
                                ))}
                              </select>
                            );
                          case 'textarea':
                            return (
                              <textarea
                                rows={2}
                                value={String(inputValue)}
                                onChange={(event) => handleValueChange(field.path, event.target.value)}
                                className="w-full bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-md px-3 py-2 focus:outline-none focus:border-slate-500"
                              />
                            );
                          case 'secret':
                            return (
                              <div className="relative">
                                <input
                                  type="password"
                                  autoComplete="new-password"
                                  placeholder={hasSecret ? 'Stored (enter to replace)' : field.placeholder}
                                  value={String(inputValue)}
                                  onChange={(event) => handleSecretChange(pathKey, event.target.value)}
                                  className="w-full bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-md px-3 py-2 focus:outline-none focus:border-slate-500"
                                />
                                {hasSecret && (
                                  <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-emerald-400">
                                    Stored
                                  </span>
                                )}
                              </div>
                            );
                          case 'number':
                            return (
                              <input
                                type="number"
                                step={field.step ?? 0.01}
                                value={String(inputValue)}
                                onChange={(event) => {
                                  const raw = event.target.value;
                                  if (raw === '') {
                                    handleValueChange(field.path, null);
                                    return;
                                  }
                                  const parsed = Number(raw);
                                  if (!Number.isNaN(parsed)) {
                                    handleValueChange(field.path, parsed);
                                  }
                                }}
                                className="w-full bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-md px-3 py-2 focus:outline-none focus:border-slate-500"
                              />
                            );
                          default:
                            return (
                              <input
                                type="text"
                                value={String(inputValue)}
                                onChange={(event) => handleValueChange(field.path, event.target.value)}
                                placeholder={field.placeholder}
                                className="w-full bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-md px-3 py-2 focus:outline-none focus:border-slate-500"
                              />
                            );
                        }
                      };

                      return (
                        <div key={pathKey} className="relative group">
                          <div className="flex items-center justify-between text-[11px] text-slate-300">
                            <span className="flex items-center gap-2">
                              <span className="font-medium">{field.label}</span>
                              <span className="text-[10px] text-slate-500">?</span>
                            </span>
                            {field.unit && <span className="text-[10px] text-slate-500">{field.unit}</span>}
                          </div>
                          <div className="mt-1">{renderInput()}</div>
                          <div className="absolute left-0 top-full mt-2 z-20 w-[320px] bg-slate-950 border border-slate-700 rounded-lg p-3 shadow-xl opacity-0 pointer-events-none group-hover:opacity-100">
                            {tooltipCopy(field.help)}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>
              ))}

              <section className="col-span-2 bg-slate-900/40 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="text-xs font-semibold text-slate-200">Settings Files</div>
                <div className="grid grid-cols-3 gap-3 text-[11px] text-slate-400">
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-slate-500">baseline</div>
                    <div className="text-slate-300 break-all">{bundle?.paths?.baseline || '--'}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-slate-500">override</div>
                    <div className="text-slate-300 break-all">{bundle?.paths?.override || '--'}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-slate-500">active</div>
                    <div className="text-slate-300 break-all">{bundle?.paths?.active || '--'}</div>
                  </div>
                </div>
              </section>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-slate-800 bg-slate-900/50 flex justify-end">
          <button onClick={onClose} className="bg-slate-800 hover:bg-slate-700 text-white px-6 py-2 rounded-lg text-sm font-semibold transition-colors">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
