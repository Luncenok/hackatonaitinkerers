import os
import uuid
import pathlib
import subprocess
import sys
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from mock_data import PATIENTS
from ws_manager import ConnectionManager
from sms import send_sms
from vision import analyze_medication_photo

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI()
manager = ConnectionManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

photo_results: dict[str, dict] = {}
alerts: list[dict] = []
call_reports: list[dict] = []

TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"


# --- Models ---

class SendSmsRequest(BaseModel):
    patient_id: str
    type: str  # "photo_link" or "medication_schedule"


class AlertRequest(BaseModel):
    severity: str
    type: str
    description: str
    patient_id: str


class CallReportRequest(BaseModel):
    patient_id: str
    duration_seconds: int
    medications_verified: int
    issues_found: int
    escalations: int
    summary: str


# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# --- Patient ---

@app.get("/api/patient/{patient_id}")
async def get_patient(patient_id: str):
    patient = PATIENTS.get(patient_id)
    if not patient:
        return {"error": "Patient not found"}
    return patient


# --- SMS ---

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


# --- Photo Upload & Vision ---

@app.get("/web-call", response_class=HTMLResponse)
async def web_call_page():
    html = (TEMPLATES_DIR / "web-call.html").read_text()
    return HTMLResponse(content=html)


@app.get("/photo/{token}", response_class=HTMLResponse)
async def photo_page(token: str):
    html = (TEMPLATES_DIR / "photo.html").read_text()
    return HTMLResponse(content=html)


@app.post("/api/upload-photo")
async def upload_photo(photo: UploadFile = File(...), token: str = Form(...)):
    image_bytes = await photo.read()
    mime_type = photo.content_type or "image/jpeg"

    try:
        found_meds = analyze_medication_photo(image_bytes, mime_type)
    except Exception as e:
        print(f"[VISION ERROR] {e}")
        # Fallback: assume no meds found in photo
        found_meds = []

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


# --- Alerts ---

@app.post("/api/alert")
async def create_alert(req: AlertRequest):
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


@app.get("/api/alerts")
async def get_alerts():
    return alerts


# --- Call Reports ---

@app.post("/api/call-report")
async def create_call_report(req: CallReportRequest):
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


@app.get("/api/call-reports")
async def get_call_reports():
    return call_reports


# --- Vapi Webhook ---

@app.post("/api/vapi-webhook")
async def vapi_webhook(payload: dict):
    """Handle all Vapi tool calls from the squad agents."""
    import json as _json
    message = payload.get("message", {})
    msg_type = message.get("type", "unknown")
    print(f"\n[VAPI WEBHOOK] message.type={msg_type}")
    print(f"[VAPI WEBHOOK] full payload keys: {list(payload.keys())}")
    print(f"[VAPI WEBHOOK] message keys: {list(message.keys())}")
    if msg_type != "tool-calls":
        print(f"[VAPI WEBHOOK] non-tool-call payload: {_json.dumps(payload, indent=2, default=str)[:2000]}")
        return {}

    results = []
    for tool_call in message.get("toolCallList", []):
        name = tool_call["function"]["name"]
        args = tool_call["function"].get("arguments", {})
        tool_call_id = tool_call["id"]
        print(f"[VAPI WEBHOOK] tool call: {name}({args})")

        result = await handle_tool_call(name, args)
        print(f"[VAPI WEBHOOK] result: {str(result)[:500]}")
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
        try:
            send_sms(phone, body)
            print(f"[SMS] Photo link sent to {phone}: {link}")
        except Exception as e:
            print(f"[SMS ERROR] Failed to send SMS: {e}")
            print(f"[SMS FALLBACK] Photo link available at: {link}")
        await manager.broadcast({
            "type": "photo_requested",
            "description": f"Photo verification requested — link: {link}",
            "token": token,
            "link": link,
        })
        return {"status": "sent", "token": token, "link": link, "message": "Photo upload link has been sent. Ask the patient to click the link and take a photo. Then call check_photo_result with this token."}

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
        try:
            send_sms(phone, body)
            print(f"[SMS] Medication schedule sent to {phone}")
        except Exception as e:
            print(f"[SMS ERROR] Failed to send medication schedule: {e}")
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


# --- Trigger Call ---

@app.post("/api/trigger-call")
async def trigger_call():
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
