"use client";

import { useEffect, useRef } from "react";
import { WSEvent } from "@/hooks/useWebSocket";

function getEventDisplay(event: WSEvent): { label: string; color: string } {
  switch (event.type) {
    case "identity_verified":
      return { label: event.description || "Identity verified", color: "bg-green-100 text-green-800" };
    case "medication_check_started":
      return { label: event.description || "Checking medications", color: "bg-blue-100 text-blue-800" };
    case "medication_checked":
      return { label: event.description || "Medication checked", color: "bg-blue-100 text-blue-800" };
    case "photo_requested":
      return { label: event.description || "Photo requested", color: "bg-purple-100 text-purple-800" };
    case "photo_analyzed":
      return { label: event.description || "Photo analyzed", color: "bg-purple-100 text-purple-800" };
    case "sms_sent":
      return { label: event.description || "SMS sent", color: "bg-indigo-100 text-indigo-800" };
    case "alert_created": {
      const alert = event.alert as { severity?: string; description?: string } | undefined;
      const isUrgent = alert?.severity === "urgent";
      return {
        label: `ALERT: ${alert?.description || "Alert created"}`,
        color: isUrgent ? "bg-red-100 text-red-800" : "bg-yellow-100 text-yellow-800",
      };
    }
    case "call_started":
      return { label: event.description || "Call started", color: "bg-green-100 text-green-800" };
    case "call_completed":
      return { label: "Call completed", color: "bg-green-100 text-green-800" };
    default:
      return { label: event.description || event.type, color: "bg-slate-100 text-slate-700" };
  }
}

export default function LiveCallFeed({ events }: { events: WSEvent[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-slate-700">Live Call Feed</h2>
      <div ref={scrollRef} className="max-h-80 space-y-2 overflow-y-auto">
        {events.length === 0 && (
          <p className="text-sm text-slate-400">Waiting for call to start...</p>
        )}
        {events.map((event, i) => {
          const { label, color } = getEventDisplay(event);
          return (
            <div
              key={i}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${color}`}
            >
              <span className="mr-2 text-xs text-slate-400">
                {new Date().toLocaleTimeString()}
              </span>
              {label}
            </div>
          );
        })}
      </div>
    </div>
  );
}
