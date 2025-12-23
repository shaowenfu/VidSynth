import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { LogEntry, LogLevel, LogStage } from '../types';

interface StatusSnapshot {
  stage: LogStage;
  status: string;
  progress: number | null;
  message?: string;
  theme?: string;
  theme_slug?: string;
  video_id?: string;
  updated_at: string;
}

interface LogContextType {
  logs: LogEntry[];
  clearLogs: () => void;
  isConnected: boolean;
  lastEvent: Record<string, any> | null;
  statusByStage: Record<string, StatusSnapshot>;
}

const LogContext = createContext<LogContextType | undefined>(undefined);

export const useLogStore = () => {
  const context = useContext(LogContext);
  if (!context) {
    throw new Error('useLogStore must be used within a LogProvider');
  }
  return context;
};

export const LogProvider: React.FC<{ children: React.ReactNode; enabled?: boolean }> = ({
  children,
  enabled = true,
}) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<Record<string, any> | null>(null);
  const [statusByStage, setStatusByStage] = useState<Record<string, StatusSnapshot>>({});
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const [connectTick, setConnectTick] = useState(0);
  const statusLogStateRef = useRef<Record<string, { status: string; bucket: number }>>({});
  const apiBase = import.meta.env.VITE_API_BASE || '';

  const addLog = (log: LogEntry) => {
    setLogs((prev) => {
      // Keep last 1000 logs
      const next = [...prev, log];
      if (next.length > 1000) {
        return next.slice(next.length - 1000);
      }
      return next;
    });
  };

  const clearLogs = () => setLogs([]);

  const mapStage = (stage: string): LogStage => {
    if (stage === 'segment') return 'segmentation';
    if (stage === 'theme_match') return 'matching';
    if (stage === 'sequence') return 'sequencing';
    if (stage === 'export') return 'export';
    if (stage === 'clustering') return 'clustering';
    if (stage === 'system') return 'system';
    return 'general';
  };

  const addStatusLog = (payload: Record<string, any>) => {
    const stage = mapStage(String(payload.stage || 'general'));
    const status = String(payload.status || 'unknown');
    const progressValue = typeof payload.progress === 'number' ? Math.round(payload.progress * 100) : null;
    const bucket = progressValue === null ? -1 : Math.floor(progressValue / 10);
    const key = `${stage}:${payload.theme_slug ?? payload.video_id ?? ''}`;
    const prev = statusLogStateRef.current[key];
    if (prev && prev.status === status && prev.bucket === bucket) {
      return;
    }
    statusLogStateRef.current[key] = { status, bucket };
    const message = [
      `STATUS ${status.toUpperCase()}`,
      progressValue !== null ? `${progressValue}%` : null,
      payload.message ? `- ${payload.message}` : null,
    ]
      .filter(Boolean)
      .join(' ');
    const entry: LogEntry = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      level: status === 'error' ? 'ERROR' : 'INFO',
      stage,
      message,
      context: { source: 'status', ...payload },
    };
    addLog(entry);
  };

  useEffect(() => {
    if (!enabled) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      setIsConnected(false);
      return;
    }

    const url = `${apiBase}/api/events`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
    };

    es.onmessage = (event) => {
        if (!event.data || event.data === ": keepalive") return;
        try {
            const payload = JSON.parse(event.data);
            
            // Check if it's a structural log message (from _global_log_listener)
            if (payload.type === 'log') {
                const entry: LogEntry = {
                    id: crypto.randomUUID(), // Simple client-side ID
                    timestamp: payload.timestamp || new Date().toISOString(),
                    level: (payload.level as LogLevel) || 'INFO',
                    stage: (payload.stage as LogStage) || 'general',
                    message: payload.message || '',
                    context: payload.context,
                    module: payload.module
                };
                addLog(entry);
                setLastEvent(payload);
            } 
            // Handle legacy/task status messages as logs too if needed, or ignore
            // For now, we mainly focus on explicit logs. 
            // Optionally, we can convert status updates to logs:
            else if (payload.status && payload.message) {
                 // Create a synthetic log for status updates to ensure visibility
                 // Avoid duplicates if the backend also logs this event
                 // (Backend transformation ensures logs are separate, so this might duplicate if not careful)
                 // Let's stick to only 'type: log' for the Console to keep it clean.
                setLastEvent(payload);
                addStatusLog(payload);
            } else {
                setLastEvent(payload);
            }

            if (payload.stage && payload.status) {
              const stage = mapStage(String(payload.stage));
              const progressValue = typeof payload.progress === 'number' ? Math.round(payload.progress * 100) : null;
              setStatusByStage((prev) => ({
                ...prev,
                [stage]: {
                  stage,
                  status: String(payload.status),
                  progress: progressValue,
                  message: payload.message,
                  theme: payload.theme,
                  theme_slug: payload.theme_slug,
                  video_id: payload.video_id,
                  updated_at: payload.updated_at || new Date().toISOString(),
                },
              }));
            }

        } catch (err) {
            console.error('LogProvider: Failed to parse SSE message', err);
        }
    };

    es.onerror = () => {
      setIsConnected(false);
      es.close();
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
      }
      reconnectTimerRef.current = window.setTimeout(() => {
        setConnectTick((prev) => prev + 1);
      }, 2000);
    };

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      setIsConnected(false);
    };
  }, [apiBase, enabled, connectTick]);

  return (
    <LogContext.Provider value={{ logs, clearLogs, isConnected, lastEvent, statusByStage }}>
      {children}
    </LogContext.Provider>
  );
};
