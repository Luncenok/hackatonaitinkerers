import { WSEvent } from "@/hooks/useWebSocket";

interface Alert {
  id: string;
  severity: string;
  type: string;
  description: string;
  timestamp: string;
}

export default function AlertsPanel({ events }: { events: WSEvent[] }) {
  const alerts = events
    .filter((e) => e.type === "alert_created")
    .map((e) => e.alert as Alert);

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-slate-700">Alerts</h2>
      <div className="max-h-80 space-y-3 overflow-y-auto">
        {alerts.length === 0 && (
          <p className="text-sm text-slate-400">No alerts yet</p>
        )}
        {alerts.map((alert, i) => {
          const isUrgent = alert.severity === "urgent";
          return (
            <div
              key={alert.id || i}
              className={`rounded-lg border-l-4 p-4 ${
                isUrgent
                  ? "border-red-500 bg-red-50"
                  : "border-yellow-500 bg-yellow-50"
              }`}
            >
              <div className="mb-1 flex items-center gap-2">
                <span
                  className={`inline-block rounded px-2 py-0.5 text-xs font-bold uppercase ${
                    isUrgent
                      ? "bg-red-600 text-white"
                      : "bg-yellow-500 text-white"
                  }`}
                >
                  {alert.severity}
                </span>
                <span className="text-xs text-slate-400">
                  {alert.type.replace(/_/g, " ")}
                </span>
              </div>
              <p className={`text-sm font-medium ${isUrgent ? "text-red-800" : "text-yellow-800"}`}>
                {alert.description}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
