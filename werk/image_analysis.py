import base64
from openai import OpenAI
from dotenv import load_dotenv
import os
from pathlib import Path
import mimetypes
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import json

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def _safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# Directory containing images
images_dir = Path("data/werk/57403")


def list_image_files(directory: Path) -> list[Path]:
    if not directory.exists() or not directory.is_dir():
        return []
    exts = {".jpg", ".jpeg", ".png"}
    files = [p for p in sorted(directory.iterdir()) if p.suffix.lower() in exts and p.is_file()]
    return files

def load_datasheet_json(building_dir: Path) -> Optional[Dict[str, Any]]:
    p = building_dir / "datasheet.json"
    if not p.exists():
        return None
    try:
        return json.loads(_safe_read_text(p))
    except Exception:
        return None
    
    
def normalize_context(datasheet: Dict[str, Any]) -> str:
    # Keep the prompt small but informative. Prefer the most relevant long text fields if present.
    preferred_order = [
        "Name",
        "Ort",
        "Gemeinde",
        "Kanton",
        "Land",
        "Strasse",
        "Nr.",
        "Fertigstellung",
        "Architektur",
        "Konstruktion",
        "Gebäudetechnik",
        "Projektinformation",
    ]

    lines: List[str] = []

    # First: preferred keys in order
    for k in preferred_order:
        if k in datasheet and datasheet[k]:
            v = datasheet[k]
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False)
            lines.append(f"{k}: {str(v).strip()}")

    # Then: the rest (short keys/values)
    for k, v in datasheet.items():
        if k in preferred_order:
            continue
        if v is None:
            continue
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        v = str(v).strip()
        if not v:
            continue
        # Avoid repeating huge blobs twice
        if len(v) > 800:
            continue
        lines.append(f"{k}: {v}")

    return "\n".join(lines).strip()

bdir = 'data/werk/57403'
datasheet = load_datasheet_json(Path(bdir))

context_text = normalize_context(datasheet)

content_items = [
    {"role": "user", "content": f"KONTEXT:\n{context_text}"}
]
# Gather images and build content list
image_files = list_image_files(images_dir)
for p in image_files:
    b64 = encode_image(p)
    mime, _ = mimetypes.guess_type(str(p))
    if not mime:
        mime = "image/jpeg"
    content_items.append({
        "type": "input_image",
        #"image_url": f"data:image/jpeg;base64,{b64}"
        "image_url": f"data:image/jpeg;base64,[IMAGE]]"
    })
    
print(content_items)
exit()


class WerkExtraction(BaseModel):
    jahr_fertigstellung: Optional[str] = Field(None, alias="Jahr (Fertigstellung)")
    Ort: Optional[str] = Field(None, alias="Ort")
    Architekt: Optional[str] = Field(None, alias="Architekt")
    Dach: Optional[str] = Field(None, alias="Dach")
    Aussenwand: Optional[str] = Field(None, alias="Aussenwand")
    Fenster: Optional[str] = Field(None, alias="Fenster")
    Tragwerk: Optional[str] = Field(None, alias="Tragwerk")
    Decke: Optional[str] = Field(None, alias="Decke")
    Innenwaende: Optional[str] = Field(None, alias="Innenwände")
    Haustechnik: Optional[str] = Field(None, alias="Haustechnik")

response = client.chat.completions.parse(

    model="gpt-5",
    messages=[
        {
            "role": "system",
            "content": (
                "Du extrahierst strukturierte Baudaten aus einem gegebenen Datenblatt-Text.\n"
                "Regeln:\n"
                "- Nutze nur Informationen aus dem bereitgestellten Kontext.\n"
                "- Wenn etwas fehlt/unklar ist: null.\n"
                '- "Jahr (Fertigstellung)" bitte als 4-stellige Jahreszahl (z.B. "1996") falls möglich; '
                "wenn nur ein Datum vorhanden ist, extrahiere das Jahr; sonst null.\n"
                '- "Architekt" aus Feld "Architektur" (Namen/Firma), ohne Zusatzrollen.\n'
                "- Dach/Aussenwand/Fenster/Tragwerk/Decke/Innenwände aus dem Abschnitt 'Konstruktion' "
                "oder ähnlichen Beschreibungen.\n"
                "- Haustechnik aus 'Gebäudetechnik' oder ähnlichen Beschreibungen.\n"
            ),
        },
        {
        "role": "user",
        "content": content_items,
        }
        ],
    response_format=WerkExtraction,
)
print(response.choices[0].message.parsed)
exit()
response = client.responses.create(
    model="gpt-4.1",
    input=[
        {
            "role": "user",
            "content": content_items,
        }
    ],
    response_format=WerkExtraction
)


print(response.choices[0].message.parsed)
print(response.output_text)
exit()

# Getting the Base64 string
base64_image = encode_image(image_path)
base64_image2 = encode_image(image_path2)



response = client.responses.create(
    model="gpt-4.1",
    input=[
        {
            "role": "user",
            "content": [
                { "type": "input_text", "text": "what's in this image?" },
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{base64_image}",
                },

                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{base64_image2}",
                },
            ],
        }
    ],
    response_format=WerkExtraction
)


print(response.choices[0].message.parsed)
print(response.output_text)