"""
Create Vapi Squad and trigger an outbound call.
Usage: python vapi/create_squad_and_call.py
       python vapi/create_squad_and_call.py --single  (fallback: single agent)
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
    triage_agent = {
        "name": "Triage Agent",
        "model": {
            "provider": "google",
            "model": "gemini-2.0-flash",
            "messages": [
                {
                    "role": "system",
                    "content": (
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
            ],
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
    }

    medication_agent = {
        "name": "Medication Agent",
        "model": {
            "provider": "google",
            "model": "gemini-2.0-flash",
            "messages": [
                {
                    "role": "system",
                    "content": (
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
            ],
        },
        "voice": {
            "provider": "vapi",
            "voiceId": "Elliot",
        },
    }

    symptom_agent = {
        "name": "Symptom Agent",
        "model": {
            "provider": "google",
            "model": "gemini-2.0-flash",
            "messages": [
                {
                    "role": "system",
                    "content": (
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
            ],
        },
        "voice": {
            "provider": "vapi",
            "voiceId": "Elliot",
        },
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
                        "description": "Transfer when identity is verified and general wellbeing has been assessed.",
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
                        "description": "Transfer when medication review is complete.",
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
    squad = build_squad()

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

    squad["members"][0]["assistant"]["model"]["tools"] = triage_tools
    squad["members"][1]["assistant"]["model"]["tools"] = medication_tools
    squad["members"][2]["assistant"]["model"]["tools"] = symptom_tools

    payload = {
        "squad": squad,
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": PATIENT_PHONE_NUMBER,
        },
        "assistantOverrides": {
            "voicemailDetectionEnabled": False,
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


def create_single_agent_call():
    """Fallback: single agent with all tools."""
    all_tools = list(TOOLS.values())

    payload = {
        "assistant": {
            "name": "AfterCare Agent",
            "voicemailDetection": {"enabled": False},
            "model": {
                "provider": "google",
                "model": "gemini-2.0-flash",
                "messages": [
                    {
                        "role": "system",
                        "content": (
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
                    }
                ],
                "tools": all_tools,
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


if __name__ == "__main__":
    import sys
    if "--single" in sys.argv:
        create_single_agent_call()
    else:
        create_outbound_call()
