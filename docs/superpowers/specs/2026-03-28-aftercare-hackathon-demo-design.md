# AfterCare Hackathon Demo — Technical Design Spec

## Overview

AfterCare is an AI voice agent that calls patients 48 hours after hospital discharge to check medications, detect symptoms, and escalate issues. This spec covers the **hackathon demo** — a working prototype for a live 5-minute stage presentation.

## Constraints

- **Timeline:** ~8 hours of building, 1 person + Claude
- **Demo environment:** Laptop + projector + phone on stage
- **Language:** English for the demo conversation, with optional Polish switch at the end
- **Data:** Hardcoded mock patient, no real hospital integration

## Priority Order

1. Live phone call (English, medication check conversation)
2. SMS with medication schedule
3. Photo-of-medications flow (Gemini Vision)
4. Real-time dashboard with alerts

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                     VAPI                             │
│                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐    │
│  │ Triage   │──>│Medication│──>│  Symptom/     │    │
│  │ Agent    │   │ Agent    │   │  Closing Agent│    │
│  └──────────┘   └──────────┘   └──────────────┘    │
│       │              │               │               │
│       └──────── Function Calls ──────┘               │
│                      │                               │
└──────────────────────┼───────────────────────────────┘
                       │
              ┌─────────────────┐
              │  FastAPI Backend │
              │                 │
              │  /api/patient   │
              │  /api/send-sms  │
              │  /photo/{token} │
              │  /api/upload    │
              │  /api/alert     │
              │  /api/call-report│
              │  /ws            │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │ Next.js Dashboard│
              │                  │
              │  Patient Info    │
              │  Live Call Feed  │
              │  Alerts          │
              │  Quality Metrics │
              └──────────────────┘
```

**Approach:** Vapi-Centric. Vapi Squads handle conversation with 3 specialized agents. Function calls hit a lightweight FastAPI backend. Dashboard connects via WebSocket for real-time updates.

**Fallback:** If Vapi Squads don't work within 2-3 hours, collapse to a single Vapi agent with the same function calls. Nothing else changes.

**Hosting:** FastAPI + Next.js run locally. ngrok exposes the backend so Vapi function calls can reach it.

---

## Vapi Squad — 3 Agents

### Agent 1: Triage Agent

**Role:** Opens call, verifies identity, assesses general state.

**Flow:**
1. Greets patient warmly
2. Asks for date of birth to verify identity
3. Asks "How are you feeling since your discharge?"
4. Listens for general state

**Handoff condition:** Identity verified and general check complete → hand off to Medication Agent.

**System prompt tone:** Warm, professional, empathetic. Speaks like a caring nurse.

### Agent 2: Medication Agent

**Role:** Reviews each prescribed medication, detects issues, triggers photo flow.

**Flow:**
1. Calls `get_patient_medications` to load discharge card
2. Asks about each medication one by one
3. If patient expresses confusion → offers photo verification
4. Sends SMS with photo upload link via `send_photo_link`
5. Waits for photo analysis result via `check_photo_result`
6. Reports findings to patient (matched meds, missing meds)
7. Sends full medication schedule via SMS using `send_medication_schedule`
8. Creates alert for any missing/wrong medication via `create_alert`

**Function calls:**
- `get_patient_medications` — returns list of prescribed meds from mock discharge card
- `send_photo_link` — sends SMS with link to photo upload page
- `check_photo_result` — gets Gemini Vision analysis result
- `send_medication_schedule` — sends SMS with formatted medication list and schedule
- `create_alert` — creates alert pushed to dashboard

**Handoff condition:** Medication review complete → hand off to Symptom Agent.

### Agent 3: Symptom & Closing Agent

**Role:** Structured symptom check, red flag detection, escalation, warm closing.

**Flow:**
1. Asks about pain, fever, wound status, breathing, any adverse reactions to medications
2. If red flag detected (e.g., adverse drug reaction, severe symptoms) → creates urgent alert via `create_alert`
3. If escalation needed → tells patient "I'm flagging this for your care team, someone will call you back shortly"
4. Closes call warmly
5. Saves structured call report via `save_call_report`

**Function calls:**
- `create_alert` — urgent escalation for red flags
- `save_call_report` — structured JSON summary of entire call, pushed to dashboard

---

## FastAPI Backend

### Mock Data

One hardcoded patient for the demo:

```json
{
  "id": "patient-001",
  "name": "John Kowalski",
  "date_of_birth": "1955-03-15",
  "phone": "+1XXXXXXXXXX",
  "discharge_date": "2026-03-26",
  "diagnosis": "Post-cholecystectomy",
  "medications": [
    {
      "name": "Paracetamol",
      "dosage": "500mg",
      "frequency": "2x daily (morning, evening)",
      "purpose": "Pain relief"
    },
    {
      "name": "Enoxaparin",
      "dosage": "40mg",
      "frequency": "1x daily (subcutaneous injection)",
      "purpose": "Blood clot prevention"
    },
    {
      "name": "Omeprazole",
      "dosage": "20mg",
      "frequency": "1x daily (morning, before food)",
      "purpose": "Stomach protection"
    }
  ]
}
```

**Demo scenario:** Patient has Paracetamol and Enoxaparin at home. Omeprazole is missing (not purchased).

### Endpoints

#### `GET /api/patient/{id}`
Returns patient info and discharge medications. Called by Medication Agent's `get_patient_medications`.

#### `POST /api/send-sms`
Sends SMS via Twilio. Request body specifies type (`photo_link` or `medication_schedule`) and patient ID. For photo link: generates a unique token and sends URL `{ngrok_url}/photo/{token}`. For medication schedule: formats meds into a readable SMS.

#### `GET /photo/{token}`
Serves a minimal HTML page with a "Take Photo" button that opens the device camera and an "Upload" button. No framework — plain HTML/JS. Mobile-optimized.

#### `POST /api/upload-photo`
Receives the photo from the upload page. Sends image to Gemini Vision API with prompt: "Identify all medication packages in this photo. Return a JSON array of objects with 'name' and 'dosage' fields." Compares result against patient's discharge card. Returns: matched meds, missing meds, unknown meds. Stores result keyed by photo token so `check_photo_result` can retrieve it. Pushes event to dashboard via WebSocket.

#### `POST /api/alert`
Creates an alert record. Pushes to dashboard via WebSocket. Request body: `{ severity: "warning" | "urgent", type: "missing_medication" | "adverse_reaction" | "red_flag", description: string, patient_id: string }`.

#### `POST /api/call-report`
Saves structured call summary. Pushes to dashboard via WebSocket. Request body: JSON with call duration, issues found, medications verified, escalations.

#### `WS /ws`
WebSocket endpoint. Dashboard connects on load. Server pushes events: `call_started`, `identity_verified`, `medication_checked`, `photo_requested`, `photo_analyzed`, `sms_sent`, `alert_created`, `call_completed`, `call_report`.

---

## Next.js Dashboard

### Layout

Single page, 2x2 grid, designed for projector readability (large fonts, high contrast).

| **Patient Info** (top-left) | **Live Call Feed** (top-right) |
|---|---|
| **Alerts** (bottom-left) | **Quality Metrics** (bottom-right) |

### Patient Info Panel
Shows John Kowalski's card: name, age (71), discharge date, diagnosis, list of prescribed medications. Static, loaded on page open via `/api/patient/patient-001`.

### Live Call Feed Panel
Real-time chronological feed of call events from WebSocket. Each event is a card with timestamp and description:
- "Call started"
- "Identity verified — DOB confirmed"
- "Medication check: Paracetamol 500mg — OK"
- "Medication check: Enoxaparin 40mg — OK"
- "Photo verification requested — SMS sent"
- "Photo received — analyzing..."
- "Photo analysis complete — Omeprazole 20mg MISSING"
- "Medication schedule SMS sent"
- "Symptom check in progress"
- "ADVERSE REACTION REPORTED: Enoxaparin — dizziness/nausea"
- "Urgent escalation created"
- "Call completed"

Events auto-scroll, new events animate in.

### Alerts Panel
Cards that appear when `alert_created` events arrive via WebSocket. Two types:
- **Warning** (yellow): Missing medication
- **Urgent** (red): Adverse reaction, red flag symptoms

Each card shows: severity badge, description, timestamp.

### Quality Metrics Panel
Simple counters that update as call progresses:
- Calls completed today: 0 → 1
- Medications verified: 0 → 3
- Issues detected: 0 → 2
- Escalations: 0 → 1

References NFZ quality indicators to tie into the pitch narrative.

### Styling
Clean medical aesthetic. White background, blue (#2563EB) primary, red (#DC2626) for urgent alerts, yellow (#F59E0B) for warnings. Sans-serif font, minimum 18px body text for projector visibility.

---

## Photo Upload Flow (Detail)

1. Medication Agent detects patient confusion about meds
2. Agent calls `send_photo_link` function
3. Backend generates unique token, sends SMS: "Please click this link and take a photo of your medications: {url}/photo/{token}"
4. Patient (you on stage) clicks link on phone
5. Simple HTML page opens with camera access
6. You photograph the pre-arranged medication boxes (Paracetamol + Enoxaparin, no Omeprazole)
7. Photo uploads to `/api/upload-photo`
8. Backend sends to Gemini Vision API for medication identification
9. Backend compares identified meds with discharge card
10. Result stored by token
11. Medication Agent calls `check_photo_result` — gets: matched [Paracetamol, Enoxaparin], missing [Omeprazole]
12. Agent tells patient: "I can see Paracetamol and Enoxaparin, that's correct. But I don't see Omeprazole, which was also prescribed. Have you picked it up from the pharmacy?"
13. Alert pushed to dashboard

**Gemini Vision prompt:**
```
Identify all medication packages visible in this photo.
For each medication found, return the brand name (or generic name) and dosage if visible.
Return as a JSON array: [{"name": "...", "dosage": "..."}]
Only include medications you can clearly identify. Do not guess.
```

---

## Demo Script

**Pre-arranged:**
- Two medication boxes on the table (or printed labels for Paracetamol 500mg and Enoxaparin 40mg)
- Dashboard open on projector
- Phone ready, not on silent
- ngrok running, Vapi configured

**Sequence (approx. 3 minutes):**

1. Open dashboard — Patient Kowalski visible, all panels empty/zero
2. Trigger outbound call (button on dashboard or direct Vapi API call)
3. Phone rings on stage, you answer
4. **Triage Agent:** "Hello, this is AfterCare calling from City Hospital regarding your recent stay. I'd like to check in on how you're doing. For verification, could you please confirm your date of birth?"
5. You: "March 15th, 1955"
6. Agent confirms identity → dashboard: "Identity verified"
7. Agent: "How are you feeling since you came home?"
8. You: "Okay I guess, but I'm a bit confused about my medications"
9. **Handoff to Medication Agent**
10. Agent calls `get_patient_medications`, asks about each med
11. You: "I have the painkillers and the injection, but I'm not sure about the rest"
12. Agent: "I'd like to help you verify. I'm sending you a link — could you take a photo of the medications you have?"
13. SMS arrives → you click → photograph pill boxes → upload
14. Agent: "I can see Paracetamol and Enoxaparin. But Omeprazole is missing — it protects your stomach. Please pick it up from the pharmacy."
15. Dashboard: alert pops — "Missing medication: Omeprazole 20mg"
16. Agent sends medication schedule SMS
17. **Handoff to Symptom Agent**
18. Agent: "Now I'd like to ask about how you're feeling physically. Any pain, fever, or difficulty breathing?"
19. You: "Actually, I've been feeling really dizzy and nauseous since I started taking the Enoxaparin"
20. Agent recognizes adverse reaction → "I'm going to flag this for your care team right away. Someone will call you back shortly. In the meantime, don't take another dose until you hear from them."
21. Dashboard: red alert — "Adverse reaction: Enoxaparin — dizziness/nausea — URGENT"
22. Agent closes warmly → call report appears on dashboard → metrics update
23. Optional: switch agent to Polish, invite judge to call

**Two alert types demonstrated:** missing medication (vision-detected) + adverse drug reaction (conversation-detected).

---

## Tech Stack Summary

| Component | Technology |
|---|---|
| Voice agent | Vapi (Squads or single agent fallback) |
| LLM for conversation | Gemini (via Vapi) |
| Vision analysis | Gemini Vision API |
| Backend | Python FastAPI |
| SMS | Twilio (via Vapi or direct) |
| Dashboard | Next.js |
| Real-time updates | WebSocket |
| Local tunnel | ngrok |
| Hosting | Local machine |

---

## Fallback Plan

If Vapi Squads don't work within 2-3 hours:
- Collapse to single Vapi agent with combined system prompt
- Same function calls, same backend, same dashboard
- Lose the handoff transitions but everything else works identically
- Demo is still impressive — multi-modal AI call with vision, SMS, real-time alerts
