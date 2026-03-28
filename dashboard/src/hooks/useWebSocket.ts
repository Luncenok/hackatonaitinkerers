"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export interface WSEvent {
  type: string;
  description?: string;
  [key: string]: unknown;
}

export function useWebSocket(url: string) {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, 2000);
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as WSEvent;
      setEvents((prev) => [...prev, data]);
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { events, connected };
}
