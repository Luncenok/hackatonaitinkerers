# AfterCare Hackathon Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working AfterCare demo — AI voice agent calls a patient post-discharge, checks medications via conversation + photo, sends SMS, escalates issues, and updates a real-time dashboard on stage.

**Architecture:** Vapi Squads (3 agents: Triage, Medication, Symptom) make outbound calls and use function calling to hit a FastAPI backend. The backend serves mock patient data, handles SMS via Twilio, photo upload + Gemini Vision analysis, and pushes events to a Next.js dashboard via WebSocket. Everything runs locally with ngrok exposing the backend.

**Tech Stack:** Vapi (voice/squads), Gemini (LLM + Vision), FastAPI (Python backend), Next.js (dashboard), Twilio (SMS), ngrok (tunnel), WebSocket (real-time)

---

## File Structure

```
hackatonaitinkerers/
├── backend/
│   ├── main.py              # FastAPI app: endpoints, WebSocket, CORS
│   ├── mock_data.py          # Hardcoded patient data
│   ├── sms.py                # Twilio SMS helper
│   ├── vision.py             # Gemini Vision analysis
│   ├── ws_manager.py         # WebSocket connection manager
│   ├── requirements.txt      # Python dependencies
│   └── templates/
│       └── photo.html        # Camera upload page (plain HTML/JS)
├── dashboard/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx    # Root layout
│   │   │   ├── page.tsx      # Main dashboard page
│   │   │   └── globals.css   # Global styles
│   │   ├── components/
│   │   │   ├── PatientInfo.tsx
│   │   │   ├── LiveCallFeed.tsx
│   │   │   ├── AlertsPanel.tsx
│   │   │   └── QualityMetrics.tsx
│   │   └── hooks/
│   │       └── useWebSocket.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── tailwind.config.ts
├── vapi/
│   └── create_squad_and_call.py  # Script to create squad + trigger outbound call
├── .env                      # API keys (gitignored)
└── .gitignore
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `.gitignore`
- Create: `.env`
- Create: `backend/requirements.txt`
- Create: `dashboard/` (via create-next-app)

- [ ] **Step 1: Initialize git repo**

```bash
cd /Users/luncenok/Projects/hackatonaitinkerers
git init
```

- [ ] **Step 2: Create .gitignore**

```gitignore
node_modules/
__pycache__/
.env
.next/
*.pyc
venv/
.venv/
```

- [ ] **Step 3: Create .env template**

```env
VAPI_API_KEY=your_vapi_key_here
TWILIO_ACCOUNT_SID=your_sid_here
TWILIO_AUTH_TOKEN=your_token_here
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
PATIENT_PHONE_NUMBER=+1XXXXXXXXXX
GOOGLE_API_KEY=your_gemini_key_here
NGROK_URL=http://localhost:8000
VAPI_PHONE_NUMBER_ID=your_vapi_phone_number_id
```

- [ ] **Step 4: Create backend/requirements.txt**

```
fastapi==0.115.0
uvicorn==0.30.0
python-dotenv==1.0.1
twilio==9.3.0
google-genai==1.10.0
python-multipart==0.0.12
```

- [ ] **Step 5: Create Python venv and install dependencies**

```bash
cd /Users/luncenok/Projects/hackatonaitinkerers
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

- [ ] **Step 6: Scaffold Next.js dashboard**

```bash
cd /Users/luncenok/Projects/hackatonaitinkerers
npx create-next-app@latest dashboard --typescript --tailwind --eslint --app --src-dir --no-import-alias --use-npm
```

When prompted, accept defaults.

- [ ] **Step 7: Commit**

```bash
git add .gitignore .env backend/requirements.txt dashboard/
git commit -m "chore: scaffold project with FastAPI backend and Next.js dashboard"
```

---

### Task 2: Backend — Mock Data & Patient Endpoint

**Files:**
- Create: `backend/mock_data.py`
- Create: `backend/ws_manager.py`
- Create: `backend/main.py`

- [ ] **Step 1: Create backend/mock_data.py**

```python
PATIENTS = {
    "patient-001": {
        "id": "patient-001",
        "name": "John Kowalski",
        "date_of_birth": "1955-03-15",
        "phone": "",  # filled from .env at runtime
        "discharge_date": "2026-03-26",
        "diagnosis": "Post-cholecystectomy",
        "medications": [
            {
                "name": "Paracetamol",
                "dosage": "500mg",
                "frequency": "2x daily (morning, evening)",
                "purpose": "Pain relief",
            },
            {
                "name": "Enoxaparin",
                "dosage": "40mg",
                "frequency": "1x daily (subcutaneous injection)",
                "purpose": "Blood clot prevention",
            },
            {
                "name": "Omeprazole",
                "dosage": "20mg",
                "frequency": "1x daily (morning, before food)",
                "purpose": "Stomach protection",
            },
        ],
    }
}
```

- [ ] **Step 2: Create backend/ws_manager.py**

```python
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)
```

- [ ] **Step 3: Create backend/main.py with patient endpoint**

```python
import os
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from mock_data import PATIENTS
from ws_manager import ConnectionManager

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI()
manager = ConnectionManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for photo analysis results
photo_results: dict[str, dict] = {}


@app.get("/api/patient/{patient_id}")
async def get_patient(patient_id: str):
    patient = PATIENTS.get(patient_id)
    if not patient:
        return {"error": "Patient not found"}
    return patient


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

- [ ] **Step 4: Test the backend starts and patient endpoint works**

```bash
cd /Users/luncenok/Projects/hackatonaitinkerers
source venv/bin/activate
cd backend && python -m uvicorn main:app --reload --port 8000 &
sleep 2
curl http://localhost:8000/api/patient/patient-001
# Expected: JSON with John Kowalski's data
kill %1
```

- [ ] **Step 5: Commit**

```bash
git add backend/mock_data.py backend/ws_manager.py backend/main.py
git commit -m "feat: add mock patient data, WebSocket manager, and patient endpoint"
```

---

### Task 3: Backend — Twilio SMS

**Files:**
- Create: `backend/sms.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create backend/sms.py**

```python
import os
from twilio.rest import Client


def get_twilio_client():
    return Client(
        os.environ["TWILIO_ACCOUNT_SID"],
        os.environ["TWILIO_AUTH_TOKEN"],
    )


def send_sms(to: str, body: str):
    client = get_twilio_client()
    message = client.messages.create(
        body=body,
        from_=os.environ["TWILIO_PHONE_NUMBER"],
        to=to,
    )
    return message.sid
```

- [ ] **Step 2: Add SMS endpoint to backend/main.py**

Add these imports at the top of `main.py`:

```python
from pydantic import BaseModel
from sms import send_sms
```

Add these models and endpoint after the existing routes:

```python
class SendSmsRequest(BaseModel):
    patient_id: str
    type: str  # "photo_link" or "medication_schedule"


@app.post("/api/send-sms")
async def send_sms_endpoint(req: SendSmsRequest):
    patient = PATIENTS.get(req.patient_id)
    if not patient:
        return {"error": "Patient not found"}

    phone = os.environ.get("PATIENT_PHONE_NUMBER", patient["phone"])

    if req.type == "photo_link":
        token = str(uuid.uuid4())[:8]
        ngrok_url = os.environ.get("NGROK_URL", "http://localhost:8000")
        link = f"{ngrok_url}/photo/{token}"
        body = (
            f"AfterCare: Please click this link and take a photo of your medications: {link}\n"
            f"This will help us verify you have all prescribed medications."
        )
        send_sms(phone, body)
        await manager.broadcast({
            "type": "photo_requested",
            "description": "Photo verification requested — SMS sent",
            "token": token,
        })
        return {"status": "sent", "token": token}

    elif req.type == "medication_schedule":
        meds_text = "\n".join(
            f"• {m['name']} {m['dosage']} — {m['frequency']} ({m['purpose']})"
            for m in patient["medications"]
        )
        body = f"AfterCare — Your medications after discharge:\n{meds_text}"
        send_sms(phone, body)
        await manager.broadcast({
            "type": "sms_sent",
            "description": "Medication schedule SMS sent",
        })
        return {"status": "sent"}

    return {"error": "Invalid SMS type"}
```

- [ ] **Step 3: Test SMS endpoint**

```bash
cd /Users/luncenok/Projects/hackatonaitinkerers/backend
source ../venv/bin/activate
python -m uvicorn main:app --reload --port 8000 &
sleep 2
curl -X POST http://localhost:8000/api/send-sms \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "patient-001", "type": "photo_link"}'
# Expected: {"status": "sent", "token": "xxxxxxxx"}
kill %1
```

- [ ] **Step 4: Commit**

```bash
git add backend/sms.py backend/main.py
git commit -m "feat: add Twilio SMS endpoint for photo link and medication schedule"
```

---

### Task 4: Backend — Photo Upload Page & Gemini Vision

**Files:**
- Create: `backend/templates/photo.html`
- Create: `backend/vision.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create backend/templates/photo.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AfterCare — Photo Upload</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f0f4f8;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            padding: 32px;
            max-width: 400px;
            width: 100%;
            box-shadow: 0 4px 24px rgba(0,0,0,0.1);
            text-align: center;
        }
        h1 { font-size: 20px; color: #1e293b; margin-bottom: 8px; }
        p { font-size: 14px; color: #64748b; margin-bottom: 24px; }
        .preview { max-width: 100%; border-radius: 8px; margin-bottom: 16px; display: none; }
        .btn {
            display: inline-block;
            padding: 14px 28px;
            border-radius: 10px;
            border: none;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            margin-bottom: 12px;
        }
        .btn-primary { background: #2563eb; color: white; }
        .btn-primary:disabled { background: #94a3b8; cursor: not-allowed; }
        .btn-secondary { background: #e2e8f0; color: #334155; }
        .status { margin-top: 16px; font-size: 14px; color: #16a34a; display: none; }
        .spinner { display: none; margin: 16px auto; width: 32px; height: 32px;
            border: 3px solid #e2e8f0; border-top-color: #2563eb;
            border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>Medication Photo</h1>
        <p>Please take a photo of your medications so we can verify them.</p>
        <img id="preview" class="preview" />
        <input type="file" id="fileInput" accept="image/*" capture="environment" style="display:none" />
        <button class="btn btn-primary" id="takePhoto" onclick="document.getElementById('fileInput').click()">
            Take Photo
        </button>
        <button class="btn btn-primary" id="uploadBtn" style="display:none" onclick="upload()">
            Send Photo
        </button>
        <div class="spinner" id="spinner"></div>
        <div class="status" id="status"></div>
    </div>
    <script>
        const token = window.location.pathname.split('/').pop();
        const fileInput = document.getElementById('fileInput');
        const preview = document.getElementById('preview');
        const uploadBtn = document.getElementById('uploadBtn');
        const takePhotoBtn = document.getElementById('takePhoto');

        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (ev) => {
                    preview.src = ev.target.result;
                    preview.style.display = 'block';
                    uploadBtn.style.display = 'block';
                    takePhotoBtn.textContent = 'Retake Photo';
                };
                reader.readAsDataURL(file);
            }
        });

        async function upload() {
            const file = fileInput.files[0];
            if (!file) return;

            uploadBtn.disabled = true;
            uploadBtn.textContent = 'Sending...';
            document.getElementById('spinner').style.display = 'block';

            const formData = new FormData();
            formData.append('photo', file);
            formData.append('token', token);

            try {
                const resp = await fetch('/api/upload-photo', { method: 'POST', body: formData });
                const data = await resp.json();
                document.getElementById('spinner').style.display = 'none';
                const status = document.getElementById('status');
                status.style.display = 'block';
                status.textContent = 'Photo received! You can return to your call.';
                uploadBtn.style.display = 'none';
                takePhotoBtn.style.display = 'none';
            } catch (err) {
                document.getElementById('spinner').style.display = 'none';
                uploadBtn.disabled = false;
                uploadBtn.textContent = 'Send Photo';
                alert('Upload failed. Please try again.');
            }
        }
    </script>
</body>
</html>
```

- [ ] **Step 2: Create backend/vision.py**

```python
import os
import base64
from google import genai


def analyze_medication_photo(image_bytes: bytes, mime_type: str) -> list[dict]:
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_image,
                        }
                    },
                    {
                        "text": (
                            "Identify all medication packages visible in this photo. "
                            "For each medication found, return the brand name (or generic name) and dosage if visible. "
                            "Return ONLY a JSON array: [{\"name\": \"...\", \"dosage\": \"...\"}] "
                            "Only include medications you can clearly identify. Do not guess."
                        ),
                    },
                ],
            }
        ],
    )

    import json
    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text)
```

- [ ] **Step 3: Add photo endpoints to backend/main.py**

Add this import at the top:

```python
from fastapi import UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from vision import analyze_medication_photo
import pathlib
```

Add these endpoints after the existing routes:

```python
TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"


@app.get("/photo/{token}", response_class=HTMLResponse)
async def photo_page(token: str):
    html = (TEMPLATES_DIR / "photo.html").read_text()
    return HTMLResponse(content=html)


@app.post("/api/upload-photo")
async def upload_photo(photo: UploadFile = File(...), token: str = Form(...)):
    image_bytes = await photo.read()
    mime_type = photo.content_type or "image/jpeg"

    # Analyze with Gemini Vision
    found_meds = analyze_medication_photo(image_bytes, mime_type)

    # Compare with patient's discharge card
    patient = PATIENTS.get("patient-001")
    prescribed = {m["name"].lower(): m for m in patient["medications"]}

    matched = []
    missing = []
    for med in patient["medications"]:
        found = any(
            med["name"].lower() in fm["name"].lower() or fm["name"].lower() in med["name"].lower()
            for fm in found_meds
        )
        if found:
            matched.append(med)
        else:
            missing.append(med)

    result = {
        "found_in_photo": found_meds,
        "matched": matched,
        "missing": missing,
    }

    # Store result for Vapi agent to retrieve
    photo_results[token] = result

    await manager.broadcast({
        "type": "photo_analyzed",
        "description": f"Photo analysis complete — {len(matched)} matched, {len(missing)} missing",
        "matched": [m["name"] for m in matched],
        "missing": [m["name"] for m in missing],
    })

    return result


@app.get("/api/photo-result/{token}")
async def get_photo_result(token: str):
    result = photo_results.get(token)
    if not result:
        return {"status": "pending"}
    return {"status": "complete", **result}
```

- [ ] **Step 4: Test photo page serves correctly**

```bash
cd /Users/luncenok/Projects/hackatonaitinkerers/backend
source ../venv/bin/activate
python -m uvicorn main:app --reload --port 8000 &
sleep 2
curl -s http://localhost:8000/photo/test123 | head -5
# Expected: <!DOCTYPE html> ...
kill %1
```

- [ ] **Step 5: Commit**

```bash
git add backend/templates/photo.html backend/vision.py backend/main.py
git commit -m "feat: add photo upload page and Gemini Vision medication analysis"
```

---

### Task 5: Backend — Alert & Call Report Endpoints

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add alert and call report models and endpoints to backend/main.py**

Add after the existing models:

```python
class AlertRequest(BaseModel):
    severity: str  # "warning" or "urgent"
    type: str  # "missing_medication", "adverse_reaction", "red_flag"
    description: str
    patient_id: str


class CallReportRequest(BaseModel):
    patient_id: str
    duration_seconds: int
    medications_verified: int
    issues_found: int
    escalations: int
    summary: str


# In-memory stores
alerts: list[dict] = []
call_reports: list[dict] = []


@app.post("/api/alert")
async def create_alert(req: AlertRequest):
    from datetime import datetime
    alert = {
        **req.model_dump(),
        "timestamp": datetime.now().isoformat(),
        "id": str(uuid.uuid4())[:8],
    }
    alerts.append(alert)
    await manager.broadcast({
        "type": "alert_created",
        "alert": alert,
    })
    return alert


@app.post("/api/call-report")
async def create_call_report(req: CallReportRequest):
    from datetime import datetime
    report = {
        **req.model_dump(),
        "timestamp": datetime.now().isoformat(),
    }
    call_reports.append(report)
    await manager.broadcast({
        "type": "call_completed",
        "report": report,
    })
    return report


@app.get("/api/alerts")
async def get_alerts():
    return alerts


@app.get("/api/call-reports")
async def get_call_reports():
    return call_reports
```

- [ ] **Step 2: Test alert endpoint**

```bash
cd /Users/luncenok/Projects/hackatonaitinkerers/backend
source ../venv/bin/activate
python -m uvicorn main:app --reload --port 8000 &
sleep 2
curl -X POST http://localhost:8000/api/alert \
  -H "Content-Type: application/json" \
  -d '{"severity":"warning","type":"missing_medication","description":"Omeprazole 20mg not found","patient_id":"patient-001"}'
# Expected: JSON with alert data + timestamp + id
kill %1
```

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: add alert and call report endpoints with WebSocket broadcast"
```

---

### Task 6: Backend — Vapi Tool Webhook Handler

**Files:**
- Modify: `backend/main.py`

Vapi sends tool calls as POST requests to a server URL. The request body contains `message.type == "tool-calls"` with a `toolCallList`. We need a single webhook endpoint that routes tool calls to the right handler.

- [ ] **Step 1: Add Vapi webhook endpoint to backend/main.py**

Add this endpoint:

```python
@app.post("/api/vapi-webhook")
async def vapi_webhook(payload: dict):
    """Handle all Vapi tool calls from the squad agents."""
    message = payload.get("message", {})

    if message.get("type") != "tool-calls":
        return {}

    results = []
    for tool_call in message.get("toolCallList", []):
        name = tool_call["function"]["name"]
        args = tool_call["function"].get("arguments", {})
        tool_call_id = tool_call["id"]

        result = await handle_tool_call(name, args)
        results.append({"toolCallId": tool_call_id, "result": str(result)})

    return {"results": results}


async def handle_tool_call(name: str, args: dict):
    if name == "get_patient_medications":
        patient_id = args.get("patient_id", "patient-001")
        patient = PATIENTS.get(patient_id)
        if not patient:
            return {"error": "Patient not found"}
        await manager.broadcast({
            "type": "medication_check_started",
            "description": "Checking patient medications against discharge card",
        })
        return {
            "patient_name": patient["name"],
            "medications": patient["medications"],
            "discharge_date": patient["discharge_date"],
            "diagnosis": patient["diagnosis"],
        }

    elif name == "send_photo_link":
        patient_id = args.get("patient_id", "patient-001")
        patient = PATIENTS.get(patient_id)
        phone = os.environ.get("PATIENT_PHONE_NUMBER", patient["phone"])
        token = str(uuid.uuid4())[:8]
        ngrok_url = os.environ.get("NGROK_URL", "http://localhost:8000")
        link = f"{ngrok_url}/photo/{token}"
        body = (
            f"AfterCare: Please click this link and take a photo of your medications: {link}\n"
            f"This will help us verify you have all prescribed medications."
        )
        send_sms(phone, body)
        await manager.broadcast({
            "type": "photo_requested",
            "description": "Photo verification requested — SMS sent",
            "token": token,
        })
        return {"status": "sent", "token": token, "message": "SMS sent with photo upload link. Ask the patient to click the link and take a photo. Then call check_photo_result with this token."}

    elif name == "check_photo_result":
        token = args.get("token", "")
        result = photo_results.get(token)
        if not result:
            return {"status": "pending", "message": "Photo not yet uploaded. Ask the patient if they have clicked the link and taken the photo."}
        return {
            "status": "complete",
            "matched": [f"{m['name']} {m['dosage']}" for m in result["matched"]],
            "missing": [f"{m['name']} {m['dosage']} — {m['purpose']}" for m in result["missing"]],
        }

    elif name == "send_medication_schedule":
        patient_id = args.get("patient_id", "patient-001")
        patient = PATIENTS.get(patient_id)
        phone = os.environ.get("PATIENT_PHONE_NUMBER", patient["phone"])
        meds_text = "\n".join(
            f"• {m['name']} {m['dosage']} — {m['frequency']} ({m['purpose']})"
            for m in patient["medications"]
        )
        missing_names = args.get("missing_medications", [])
        if missing_names:
            meds_text += "\n\n⚠️ PLEASE PICK UP FROM PHARMACY:\n"
            meds_text += "\n".join(f"• {name}" for name in missing_names)
        body = f"AfterCare — Your medications after discharge:\n{meds_text}"
        send_sms(phone, body)
        await manager.broadcast({
            "type": "sms_sent",
            "description": "Medication schedule SMS sent to patient",
        })
        return {"status": "sent", "message": "Medication schedule SMS sent to patient."}

    elif name == "create_alert":
        severity = args.get("severity", "warning")
        alert_type = args.get("type", "general")
        description = args.get("description", "")
        patient_id = args.get("patient_id", "patient-001")
        from datetime import datetime
        alert = {
            "severity": severity,
            "type": alert_type,
            "description": description,
            "patient_id": patient_id,
            "timestamp": datetime.now().isoformat(),
            "id": str(uuid.uuid4())[:8],
        }
        alerts.append(alert)
        await manager.broadcast({
            "type": "alert_created",
            "alert": alert,
        })
        return {"status": "created", "alert_id": alert["id"]}

    elif name == "save_call_report":
        from datetime import datetime
        report = {
            "patient_id": args.get("patient_id", "patient-001"),
            "duration_seconds": args.get("duration_seconds", 0),
            "medications_verified": args.get("medications_verified", 0),
            "issues_found": args.get("issues_found", 0),
            "escalations": args.get("escalations", 0),
            "summary": args.get("summary", ""),
            "timestamp": datetime.now().isoformat(),
        }
        call_reports.append(report)
        await manager.broadcast({
            "type": "call_completed",
            "report": report,
        })
        return {"status": "saved"}

    elif name == "report_medication_status":
        med_name = args.get("medication_name", "")
        status = args.get("status", "")
        await manager.broadcast({
            "type": "medication_checked",
            "description": f"Medication check: {med_name} — {status}",
        })
        return {"status": "reported"}

    elif name == "report_identity_verified":
        await manager.broadcast({
            "type": "identity_verified",
            "description": "Identity verified — DOB confirmed",
        })
        return {"status": "reported"}

    return {"error": f"Unknown tool: {name}"}
```

- [ ] **Step 2: Test Vapi webhook with a mock tool call**

```bash
cd /Users/luncenok/Projects/hackatonaitinkerers/backend
source ../venv/bin/activate
python -m uvicorn main:app --reload --port 8000 &
sleep 2
curl -X POST http://localhost:8000/api/vapi-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "tool-calls",
      "toolCallList": [{
        "id": "test-call-1",
        "function": {
          "name": "get_patient_medications",
          "arguments": {"patient_id": "patient-001"}
        }
      }]
    }
  }'
# Expected: {"results": [{"toolCallId": "test-call-1", "result": "...medications..."}]}
kill %1
```

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: add Vapi tool call webhook handler for all agent functions"
```

---

### Task 7: Vapi Squad Configuration & Outbound Call Script

**Files:**
- Create: `vapi/create_squad_and_call.py`

- [ ] **Step 1: Create vapi/create_squad_and_call.py**

```python
"""
Create Vapi Squad and trigger an outbound call.
Usage: python vapi/create_squad_and_call.py
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.environ["VAPI_API_KEY"]
NGROK_URL = os.environ["NGROK_URL"]
VAPI_PHONE_NUMBER_ID = os.environ["VAPI_PHONE_NUMBER_ID"]
PATIENT_PHONE_NUMBER = os.environ["PATIENT_PHONE_NUMBER"]

HEADERS = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json",
}

TOOL_SERVER = {"url": f"{NGROK_URL}/api/vapi-webhook"}

# Tool definitions shared across agents
TOOLS = {
    "get_patient_medications": {
        "type": "function",
        "function": {
            "name": "get_patient_medications",
            "description": "Retrieve the patient's prescribed medications from their discharge card. Call this at the start of medication review.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "The patient ID. Use 'patient-001'."},
                },
                "required": ["patient_id"],
            },
        },
        "server": TOOL_SERVER,
    },
    "report_identity_verified": {
        "type": "function",
        "function": {
            "name": "report_identity_verified",
            "description": "Report that the patient's identity has been verified. Call this after confirming date of birth.",
            "parameters": {"type": "object", "properties": {}},
        },
        "server": TOOL_SERVER,
    },
    "report_medication_status": {
        "type": "function",
        "function": {
            "name": "report_medication_status",
            "description": "Report the status of a single medication check to the dashboard. Call this for each medication after discussing it with the patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "medication_name": {"type": "string", "description": "Name of the medication"},
                    "status": {"type": "string", "description": "Status: 'OK', 'MISSING', 'CONFUSED', 'WRONG_DOSAGE'"},
                },
                "required": ["medication_name", "status"],
            },
        },
        "server": TOOL_SERVER,
    },
    "send_photo_link": {
        "type": "function",
        "function": {
            "name": "send_photo_link",
            "description": "Send an SMS to the patient with a link to take a photo of their medications. Use when patient is confused about their medications or you want to verify visually.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "The patient ID. Use 'patient-001'."},
                },
                "required": ["patient_id"],
            },
        },
        "server": TOOL_SERVER,
    },
    "check_photo_result": {
        "type": "function",
        "function": {
            "name": "check_photo_result",
            "description": "Check if the patient's medication photo has been analyzed. Returns matched and missing medications. Call after sending photo link and giving the patient time to take the photo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "token": {"type": "string", "description": "The token returned by send_photo_link"},
                },
                "required": ["token"],
            },
        },
        "server": TOOL_SERVER,
    },
    "send_medication_schedule": {
        "type": "function",
        "function": {
            "name": "send_medication_schedule",
            "description": "Send the patient an SMS with their full medication schedule. Include any missing medications flagged as needing pickup.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "The patient ID. Use 'patient-001'."},
                    "missing_medications": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of missing medication names to flag in the SMS",
                    },
                },
                "required": ["patient_id"],
            },
        },
        "server": TOOL_SERVER,
    },
    "create_alert": {
        "type": "function",
        "function": {
            "name": "create_alert",
            "description": "Create an alert for the medical team. Use for missing medications, adverse reactions, or concerning symptoms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["warning", "urgent"], "description": "'warning' for missing meds, 'urgent' for adverse reactions or dangerous symptoms"},
                    "type": {"type": "string", "enum": ["missing_medication", "adverse_reaction", "red_flag"], "description": "Type of alert"},
                    "description": {"type": "string", "description": "Human-readable description of the issue"},
                    "patient_id": {"type": "string", "description": "The patient ID. Use 'patient-001'."},
                },
                "required": ["severity", "type", "description", "patient_id"],
            },
        },
        "server": TOOL_SERVER,
    },
    "save_call_report": {
        "type": "function",
        "function": {
            "name": "save_call_report",
            "description": "Save a structured report at the end of the call summarizing everything that was discussed and any issues found.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "Use 'patient-001'"},
                    "duration_seconds": {"type": "integer", "description": "Approximate call duration in seconds"},
                    "medications_verified": {"type": "integer", "description": "Number of medications discussed"},
                    "issues_found": {"type": "integer", "description": "Number of issues found"},
                    "escalations": {"type": "integer", "description": "Number of urgent escalations"},
                    "summary": {"type": "string", "description": "Brief summary of the call"},
                },
                "required": ["patient_id", "summary"],
            },
        },
        "server": TOOL_SERVER,
    },
}


def build_squad():
    """Build the squad configuration with 3 agents."""

    triage_agent = {
        "name": "Triage Agent",
        "model": {
            "provider": "google",
            "model": "gemini-2.0-flash",
        },
        "voice": {
            "provider": "vapi",
            "voiceId": "Elliot",
        },
        "firstMessage": (
            "Hello, this is AfterCare calling from City Hospital regarding your recent stay. "
            "We'd like to check in on how you're doing after your discharge. "
            "For verification purposes, could you please confirm your date of birth?"
        ),
        "firstMessageMode": "assistant-speaks-first",
        "systemPrompt": (
            "You are a warm and caring follow-up nurse calling a patient who was recently discharged from the hospital. "
            "Your name is AfterCare and you're calling from City Hospital.\n\n"
            "Your tasks in this call:\n"
            "1. Verify the patient's identity by asking for their date of birth. The correct DOB is March 15, 1955. "
            "If they confirm correctly, call the report_identity_verified function.\n"
            "2. Ask how they're feeling in general since their discharge.\n"
            "3. Once identity is verified and you've asked about their general state, tell them you'll now review their medications, "
            "and the conversation will continue with a specialist.\n\n"
            "Be warm, empathetic, and patient. Speak clearly and simply. "
            "Do NOT discuss medications in detail — that's the next agent's job.\n"
            "Do NOT end the call. After your tasks, the call will transfer automatically."
        ),
    }

    medication_agent = {
        "name": "Medication Agent",
        "model": {
            "provider": "google",
            "model": "gemini-2.0-flash",
        },
        "voice": {
            "provider": "vapi",
            "voiceId": "Elliot",
        },
        "systemPrompt": (
            "You are a medication review specialist following up with a patient after hospital discharge. "
            "The patient's identity has already been verified.\n\n"
            "Your tasks:\n"
            "1. Call get_patient_medications to load the patient's discharge card (use patient_id 'patient-001').\n"
            "2. Go through EACH medication one by one. For each, ask: 'Do you have [medication name]? Are you taking it as prescribed — [frequency]?'\n"
            "3. After discussing each medication, call report_medication_status with the medication name and status.\n"
            "4. If the patient seems confused about which medications they have, offer to help verify visually: "
            "'I can send you a link to take a photo of your medications, and I'll check them for you.' "
            "Then call send_photo_link.\n"
            "5. After sending the photo link, wait a moment and then call check_photo_result with the token. "
            "If status is 'pending', tell the patient to take their time and try again in a few seconds.\n"
            "6. Report findings: tell the patient which medications matched and which are missing.\n"
            "7. For any missing medication, call create_alert with severity 'warning' and type 'missing_medication'.\n"
            "8. Call send_medication_schedule to send the patient their full medication list via SMS. "
            "Include any missing medication names in the missing_medications array.\n"
            "9. After medication review is complete, tell the patient you'll now check on their symptoms.\n\n"
            "Be patient and clear. Use simple language. Do NOT end the call."
        ),
    }

    symptom_agent = {
        "name": "Symptom Agent",
        "model": {
            "provider": "google",
            "model": "gemini-2.0-flash",
        },
        "voice": {
            "provider": "vapi",
            "voiceId": "Elliot",
        },
        "systemPrompt": (
            "You are a symptom assessment specialist following up with a patient after hospital discharge. "
            "Medications have already been reviewed.\n\n"
            "Your tasks:\n"
            "1. Ask about symptoms systematically: pain levels, fever, wound healing (if applicable), breathing, nausea, dizziness.\n"
            "2. Listen carefully for RED FLAGS: severe pain, high fever, difficulty breathing, chest pain, "
            "adverse reactions to medications (dizziness, nausea, rash after starting a medication).\n"
            "3. If the patient reports any concerning symptom — especially an adverse drug reaction — "
            "call create_alert with severity 'urgent' and type 'adverse_reaction' or 'red_flag'. "
            "Tell the patient: 'I'm going to flag this for your care team right away. Someone will call you back shortly. "
            "In the meantime, please [appropriate advice, e.g., don't take another dose until you hear from them].'\n"
            "4. If no red flags, reassure the patient that everything sounds normal.\n"
            "5. Close the call warmly: 'Thank you for your time. Remember, if you have any concerns, "
            "don't hesitate to contact the hospital. We wish you a speedy recovery.'\n"
            "6. After closing, call save_call_report with a summary of the entire call.\n\n"
            "Be empathetic and thorough but efficient."
        ),
    }

    squad = {
        "members": [
            {
                "assistant": triage_agent,
                "assistantDestinations": [
                    {
                        "type": "assistant",
                        "assistantName": "Medication Agent",
                        "message": "Let me connect you with our medication specialist who will review your prescriptions.",
                        "description": "Transfer when identity is verified and general wellbeing has been assessed. Transfer after calling report_identity_verified and asking about general state.",
                    }
                ],
            },
            {
                "assistant": medication_agent,
                "assistantDestinations": [
                    {
                        "type": "assistant",
                        "assistantName": "Symptom Agent",
                        "message": "Now let me connect you with someone who will check on your symptoms.",
                        "description": "Transfer when medication review is complete — all medications have been discussed, photo analysis done if needed, medication schedule SMS sent, and any alerts created.",
                    }
                ],
            },
            {
                "assistant": symptom_agent,
            },
        ],
    }

    return squad


def create_outbound_call():
    """Create an outbound call using the squad."""
    squad = build_squad()

    # Attach tools to each member's assistant
    all_tool_defs = list(TOOLS.values())

    triage_tools = [TOOLS["report_identity_verified"]]
    medication_tools = [
        TOOLS["get_patient_medications"],
        TOOLS["report_medication_status"],
        TOOLS["send_photo_link"],
        TOOLS["check_photo_result"],
        TOOLS["send_medication_schedule"],
        TOOLS["create_alert"],
    ]
    symptom_tools = [
        TOOLS["create_alert"],
        TOOLS["save_call_report"],
    ]

    squad["members"][0]["assistant"]["tools"] = triage_tools
    squad["members"][1]["assistant"]["tools"] = medication_tools
    squad["members"][2]["assistant"]["tools"] = symptom_tools

    payload = {
        "squad": squad,
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": PATIENT_PHONE_NUMBER,
        },
    }

    print("Creating outbound call...")
    print(json.dumps(payload, indent=2))

    resp = requests.post(
        "https://api.vapi.ai/call",
        headers=HEADERS,
        json=payload,
    )

    print(f"\nStatus: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))
    return resp.json()


if __name__ == "__main__":
    create_outbound_call()
```

- [ ] **Step 2: Test script loads without errors (dry run)**

```bash
cd /Users/luncenok/Projects/hackatonaitinkerers
source venv/bin/activate
python -c "from vapi.create_squad_and_call import build_squad; import json; print(json.dumps(build_squad(), indent=2)[:500])"
# Expected: prints squad JSON structure
```

- [ ] **Step 3: Commit**

```bash
git add vapi/create_squad_and_call.py
git commit -m "feat: add Vapi squad configuration with 3 agents and outbound call script"
```

---

### Task 8: Dashboard — Layout & WebSocket Hook

**Files:**
- Modify: `dashboard/src/app/layout.tsx`
- Modify: `dashboard/src/app/globals.css`
- Create: `dashboard/src/hooks/useWebSocket.ts`
- Modify: `dashboard/src/app/page.tsx`

- [ ] **Step 1: Create dashboard/src/hooks/useWebSocket.ts**

```typescript
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
```

- [ ] **Step 2: Replace dashboard/src/app/globals.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --primary: #2563eb;
  --urgent: #dc2626;
  --warning: #f59e0b;
  --success: #16a34a;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #f0f4f8;
}
```

- [ ] **Step 3: Replace dashboard/src/app/layout.tsx**

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AfterCare Dashboard",
  description: "Post-discharge patient follow-up monitoring",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 4: Create initial dashboard/src/app/page.tsx**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useWebSocket, WSEvent } from "@/hooks/useWebSocket";
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

  useEffect(() => {
    fetch(`${API_URL}/api/patient/patient-001`)
      .then((r) => r.json())
      .then(setPatient)
      .catch(console.error);
  }, []);

  return (
    <div className="min-h-screen p-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">AfterCare</h1>
          <p className="text-sm text-slate-500">Post-Discharge Follow-Up Monitor</p>
        </div>
        <div className={`flex items-center gap-2 text-sm ${connected ? "text-green-600" : "text-red-500"}`}>
          <span className={`inline-block h-2 w-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`} />
          {connected ? "Connected" : "Disconnected"}
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
```

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/hooks/useWebSocket.ts dashboard/src/app/globals.css dashboard/src/app/layout.tsx dashboard/src/app/page.tsx
git commit -m "feat: add dashboard layout, WebSocket hook, and main page"
```

---

### Task 9: Dashboard — PatientInfo & LiveCallFeed Components

**Files:**
- Create: `dashboard/src/components/PatientInfo.tsx`
- Create: `dashboard/src/components/LiveCallFeed.tsx`

- [ ] **Step 1: Create dashboard/src/components/PatientInfo.tsx**

```tsx
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
```

- [ ] **Step 2: Create dashboard/src/components/LiveCallFeed.tsx**

```tsx
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
    case "alert_created":
      const alert = event.alert as { severity?: string; description?: string } | undefined;
      const isUrgent = alert?.severity === "urgent";
      return {
        label: `ALERT: ${alert?.description || "Alert created"}`,
        color: isUrgent ? "bg-red-100 text-red-800" : "bg-yellow-100 text-yellow-800",
      };
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
              className={`animate-in fade-in slide-in-from-bottom-2 rounded-lg px-4 py-2 text-sm font-medium ${color}`}
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
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/PatientInfo.tsx dashboard/src/components/LiveCallFeed.tsx
git commit -m "feat: add PatientInfo and LiveCallFeed dashboard components"
```

---

### Task 10: Dashboard — AlertsPanel & QualityMetrics Components

**Files:**
- Create: `dashboard/src/components/AlertsPanel.tsx`
- Create: `dashboard/src/components/QualityMetrics.tsx`

- [ ] **Step 1: Create dashboard/src/components/AlertsPanel.tsx**

```tsx
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
```

- [ ] **Step 2: Create dashboard/src/components/QualityMetrics.tsx**

```tsx
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
          Tracking readmission risk factors per Rozporz&#261;dzenie MZ (Dz.U. 2024 poz. 1349)
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/AlertsPanel.tsx dashboard/src/components/QualityMetrics.tsx
git commit -m "feat: add AlertsPanel and QualityMetrics dashboard components"
```

---

### Task 11: Dashboard — Add "Trigger Call" Button

**Files:**
- Modify: `dashboard/src/app/page.tsx`

A button on the dashboard to trigger the outbound call via a backend endpoint, so you don't have to run a script from the terminal during the demo.

- [ ] **Step 1: Add trigger endpoint to backend/main.py**

Add this import and endpoint:

```python
import subprocess
import sys


@app.post("/api/trigger-call")
async def trigger_call():
    """Trigger the outbound call by running the Vapi script."""
    result = subprocess.run(
        [sys.executable, "vapi/create_squad_and_call.py"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), ".."),
    )
    await manager.broadcast({
        "type": "call_started",
        "description": "Outbound call initiated",
    })
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
```

- [ ] **Step 2: Add trigger button to dashboard/src/app/page.tsx**

Add a button in the header section, after the connection status div:

```tsx
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Inside the component, add state:
const [calling, setCalling] = useState(false);

async function triggerCall() {
  setCalling(true);
  try {
    await fetch(`${API_URL}/api/trigger-call`, { method: "POST" });
  } catch (err) {
    console.error("Failed to trigger call:", err);
  }
  setCalling(false);
}
```

Update the header to include the button:

```tsx
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
```

- [ ] **Step 3: Commit**

```bash
git add backend/main.py dashboard/src/app/page.tsx
git commit -m "feat: add trigger call button to dashboard and backend endpoint"
```

---

### Task 12: Environment Setup & ngrok Integration

**Files:**
- Modify: `.env` (user fills in real values)

- [ ] **Step 1: Fill in .env with real API keys**

Open `.env` and replace all placeholder values:

```env
VAPI_API_KEY=<your real key>
TWILIO_ACCOUNT_SID=<your real SID>
TWILIO_AUTH_TOKEN=<your real token>
TWILIO_PHONE_NUMBER=<your Twilio number, e.g. +1234567890>
PATIENT_PHONE_NUMBER=<your phone number to receive the demo call>
GOOGLE_API_KEY=<your Gemini API key>
NGROK_URL=http://localhost:8000
VAPI_PHONE_NUMBER_ID=<your Vapi phone number ID>
```

- [ ] **Step 2: Install ngrok if not already installed**

```bash
brew install ngrok
```

- [ ] **Step 3: Start the backend**

```bash
cd /Users/luncenok/Projects/hackatonaitinkerers
source venv/bin/activate
cd backend && python -m uvicorn main:app --reload --port 8000
```

- [ ] **Step 4: Start ngrok in a separate terminal**

```bash
ngrok http 8000
```

Copy the HTTPS forwarding URL (e.g., `https://xxxx-xx-xx-xxx-xxx.ngrok-free.app`).

- [ ] **Step 5: Update .env with ngrok URL**

```env
NGROK_URL=https://xxxx-xx-xx-xxx-xxx.ngrok-free.app
```

Restart the backend after updating.

- [ ] **Step 6: Start the dashboard in a separate terminal**

```bash
cd /Users/luncenok/Projects/hackatonaitinkerers/dashboard
npm run dev
```

Dashboard runs at `http://localhost:3000`.

- [ ] **Step 7: Verify end-to-end**

1. Open `http://localhost:3000` — should see dashboard with patient info loaded
2. Open browser console — should see WebSocket connected
3. Test webhook manually:

```bash
curl -X POST https://YOUR-NGROK-URL/api/vapi-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "tool-calls",
      "toolCallList": [{
        "id": "test-1",
        "function": {
          "name": "report_identity_verified",
          "arguments": {}
        }
      }]
    }
  }'
```

Check dashboard — "Identity verified" should appear in Live Call Feed.

---

### Task 13: End-to-End Demo Test

- [ ] **Step 1: Trigger test call**

Click "Start Follow-Up Call" on the dashboard, or run:

```bash
cd /Users/luncenok/Projects/hackatonaitinkerers
source venv/bin/activate
python vapi/create_squad_and_call.py
```

- [ ] **Step 2: Walk through the demo script**

Follow the demo script from the spec:
1. Answer the phone
2. Confirm DOB (March 15, 1955)
3. Express confusion about medications
4. When asked, say you have painkillers and the injection but not sure about the rest
5. When agent offers photo verification, wait for SMS, click link, photograph pre-arranged pill boxes
6. Confirm you didn't pick up Omeprazole
7. When symptom agent asks, report dizziness/nausea from Enoxaparin
8. Verify dashboard updates in real time

- [ ] **Step 3: Note any issues and iterate**

If Squads don't handoff correctly, check system prompts and handoff descriptions. If tools fail, check ngrok URL in `.env` and backend logs.

- [ ] **Step 4: If Squads fail — fallback to single agent**

In `vapi/create_squad_and_call.py`, add a fallback function:

```python
def create_single_agent_call():
    """Fallback: single agent with all tools."""
    all_tools = list(TOOLS.values())

    payload = {
        "assistant": {
            "name": "AfterCare Agent",
            "model": {
                "provider": "google",
                "model": "gemini-2.0-flash",
            },
            "voice": {
                "provider": "vapi",
                "voiceId": "Elliot",
            },
            "firstMessage": (
                "Hello, this is AfterCare calling from City Hospital regarding your recent stay. "
                "We'd like to check in on how you're doing after your discharge. "
                "For verification purposes, could you please confirm your date of birth?"
            ),
            "firstMessageMode": "assistant-speaks-first",
            "systemPrompt": (
                "You are AfterCare, a warm and caring follow-up nurse calling a patient discharged from City Hospital.\n\n"
                "Your call has 3 phases:\n\n"
                "PHASE 1 — IDENTITY & GENERAL CHECK:\n"
                "1. Verify identity by asking date of birth. Correct DOB: March 15, 1955.\n"
                "2. Call report_identity_verified after confirmation.\n"
                "3. Ask how they're feeling generally.\n\n"
                "PHASE 2 — MEDICATION REVIEW:\n"
                "1. Call get_patient_medications (patient_id: 'patient-001').\n"
                "2. Ask about each medication one by one. After each, call report_medication_status.\n"
                "3. If patient is confused, offer photo verification: call send_photo_link.\n"
                "4. After photo is sent, wait then call check_photo_result with the token.\n"
                "5. Report matched and missing medications to patient.\n"
                "6. For missing meds, call create_alert (severity: 'warning', type: 'missing_medication').\n"
                "7. Call send_medication_schedule with any missing medication names.\n\n"
                "PHASE 3 — SYMPTOM CHECK:\n"
                "1. Ask about pain, fever, breathing, dizziness, nausea.\n"
                "2. If adverse reaction or red flag: call create_alert (severity: 'urgent').\n"
                "3. Tell patient care team will call back. Advise to stop medication if adverse reaction.\n"
                "4. Close warmly.\n"
                "5. Call save_call_report with summary.\n\n"
                "Be warm, empathetic, patient. Use simple language. One topic at a time."
            ),
            "tools": all_tools,
        },
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": PATIENT_PHONE_NUMBER,
        },
    }

    print("Creating single-agent outbound call (fallback)...")
    resp = requests.post(
        "https://api.vapi.ai/call",
        headers=HEADERS,
        json=payload,
    )
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))
    return resp.json()
```

Update the `__main__` block:

```python
if __name__ == "__main__":
    import sys
    if "--single" in sys.argv:
        create_single_agent_call()
    else:
        create_outbound_call()
```

Run fallback with: `python vapi/create_squad_and_call.py --single`

- [ ] **Step 5: Commit final state**

```bash
git add -A
git commit -m "feat: add single-agent fallback and complete end-to-end demo setup"
```
