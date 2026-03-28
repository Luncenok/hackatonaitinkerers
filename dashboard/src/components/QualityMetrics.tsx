import { WSEvent } from "@/hooks/useWebSocket";

export default function QualityMetrics({ events }: { events: WSEvent[] }) {
  const callsCompleted = events.filter((e) => e.type === "call_completed").length;
  const medsChecked = events.filter((e) => e.type === "medication_checked").length;
  const alertEvents = events.filter((e) => e.type === "alert_created");
  const issuesDetected = alertEvents.length;
  const escalations = alertEvents.filter(
    (e) => (e.alert as { severity?: string })?.severity === "urgent"
  ).length;

  const metrics = [
    { label: "Calls Completed", value: callsCompleted, color: "text-blue-600" },
    { label: "Medications Verified", value: medsChecked, color: "text-green-600" },
    { label: "Issues Detected", value: issuesDetected, color: "text-yellow-600" },
    { label: "Escalations", value: escalations, color: "text-red-600" },
  ];

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-slate-700">Quality Metrics</h2>
      <div className="grid grid-cols-2 gap-4">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-lg bg-slate-50 p-4 text-center">
            <p className={`text-3xl font-bold ${m.color}`}>{m.value}</p>
            <p className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-400">
              {m.label}
            </p>
          </div>
        ))}
      </div>
      <div className="mt-4 rounded-lg bg-blue-50 p-3">
        <p className="text-xs font-medium text-blue-600">
          NFZ Quality Indicators Compliance
        </p>
        <p className="text-xs text-blue-500">
          Tracking readmission risk factors per Rozporządzenie MZ (Dz.U. 2024 poz. 1349)
        </p>
      </div>
    </div>
  );
}
