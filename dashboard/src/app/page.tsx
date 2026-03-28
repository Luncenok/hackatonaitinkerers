"use client";

import { useEffect, useState } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import PatientInfo from "@/components/PatientInfo";
import LiveCallFeed from "@/components/LiveCallFeed";
import AlertsPanel from "@/components/AlertsPanel";
import QualityMetrics from "@/components/QualityMetrics";

interface Patient {
  id: string;
  name: string;
  date_of_birth: string;
  discharge_date: string;
  diagnosis: string;
  medications: { name: string; dosage: string; frequency: string; purpose: string }[];
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Dashboard() {
  const { events, connected } = useWebSocket(WS_URL);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [calling, setCalling] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/patient/patient-001`)
      .then((r) => r.json())
      .then(setPatient)
      .catch(console.error);
  }, []);

  async function triggerCall() {
    setCalling(true);
    try {
      await fetch(`${API_URL}/api/trigger-call`, { method: "POST" });
    } catch (err) {
      console.error("Failed to trigger call:", err);
    }
    setCalling(false);
  }

  return (
    <div className="min-h-screen p-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">AfterCare</h1>
          <p className="text-sm text-slate-500">Post-Discharge Follow-Up Monitor</p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={triggerCall}
            disabled={calling}
            className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-semibold text-white shadow hover:bg-blue-700 disabled:bg-slate-400"
          >
            {calling ? "Calling..." : "Start Follow-Up Call"}
          </button>
          <div className={`flex items-center gap-2 text-sm ${connected ? "text-green-600" : "text-red-500"}`}>
            <span className={`inline-block h-2 w-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`} />
            {connected ? "Connected" : "Disconnected"}
          </div>
        </div>
      </header>
      <div className="grid grid-cols-2 gap-6">
        <PatientInfo patient={patient} />
        <LiveCallFeed events={events} />
        <AlertsPanel events={events} />
        <QualityMetrics events={events} />
      </div>
    </div>
  );
}
