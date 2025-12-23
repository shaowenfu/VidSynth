import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { LogEntry, LogLevel, LogStage } from '../types';

interface LogContextType {
  logs: LogEntry[];
  clearLogs: () => void;
  isConnected: boolean;
}

const LogContext = createContext<LogContextType | undefined>(undefined);

export const useLogStore = () => {
  const context = useContext(LogContext);
  if (!context) {
    throw new Error('useLogStore must be used within a LogProvider');
  }
  return context;
};

export const LogProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
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

  useEffect(() => {
    const url = `${apiBase}/api/events`;
    console.log(`LogProvider: Connecting to SSE at ${url}`);
    
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
      console.log('LogProvider: SSE Connected');
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
            } 
            // Handle legacy/task status messages as logs too if needed, or ignore
            // For now, we mainly focus on explicit logs. 
            // Optionally, we can convert status updates to logs:
            else if (payload.status && payload.message) {
                 // Create a synthetic log for status updates to ensure visibility
                 // Avoid duplicates if the backend also logs this event
                 // (Backend transformation ensures logs are separate, so this might duplicate if not careful)
                 // Let's stick to only 'type: log' for the Console to keep it clean.
            }

        } catch (err) {
            console.error('LogProvider: Failed to parse SSE message', err);
        }
    };

    es.onerror = (err) => {
      console.error('LogProvider: SSE Error', err);
      setIsConnected(false);
      es.close();
      // Simple reconnect logic could be added here
      setTimeout(() => {
          // Trigger re-render to retry effect? 
          // For MVP, we just let it close. 
          // Real prod should have robust retry.
      }, 5000);
    };

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setIsConnected(false);
    };
  }, [apiBase]);

  return (
    <LogContext.Provider value={{ logs, clearLogs, isConnected }}>
      {children}
    </LogContext.Provider>
  );
};
