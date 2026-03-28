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
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text)
