interface Medication {
  name: string;
  dosage: string;
  frequency: string;
  purpose: string;
}

interface Patient {
  id: string;
  name: string;
  date_of_birth: string;
  discharge_date: string;
  diagnosis: string;
  medications: Medication[];
}

export default function PatientInfo({ patient }: { patient: Patient | null }) {
  if (!patient) {
    return (
      <div className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-slate-700">Patient Info</h2>
        <p className="text-slate-400">Loading...</p>
      </div>
    );
  }

  const age = new Date().getFullYear() - new Date(patient.date_of_birth).getFullYear();

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-slate-700">Patient Info</h2>
      <div className="mb-4 space-y-1">
        <p className="text-2xl font-bold text-slate-800">{patient.name}</p>
        <p className="text-sm text-slate-500">Age {age} &middot; DOB {patient.date_of_birth}</p>
        <p className="text-sm text-slate-500">Discharged: {patient.discharge_date}</p>
        <p className="mt-2 inline-block rounded-full bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700">
          {patient.diagnosis}
        </p>
      </div>
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
        Prescribed Medications
      </h3>
      <div className="space-y-2">
        {patient.medications.map((med) => (
          <div key={med.name} className="rounded-lg bg-slate-50 p-3">
            <p className="font-medium text-slate-700">
              {med.name} <span className="text-slate-400">{med.dosage}</span>
            </p>
            <p className="text-sm text-slate-500">{med.frequency} &middot; {med.purpose}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
