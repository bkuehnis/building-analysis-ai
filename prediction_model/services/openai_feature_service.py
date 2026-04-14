import base64
import mimetypes
from typing import List
from openai import OpenAI

from models.building_image_schema import BuildingImageExtraction


def image_to_data_url(path: str) -> str:
    mime_type, _ = mimetypes.guess_type(path)

    if mime_type is None:
        mime_type = "image/jpeg"  # fallback

    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{b64}"

class OpenAIFeatureService:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract_features(self, image_paths: List[str]) -> BuildingImageExtraction:
        content = [{
            "type": "text",
            "text": (
                "Extrahiere Gebäude-Features aus den folgenden Bildern.\n"
                "Nutze alle Perspektiven gemeinsam.\n"
                "Luftansicht: Beziehe dich nur auf das markierte Gebäude, nutze das hilfe das zoomed Bild.\n"
                "Beziehe dich nur auf das Gebäude, welches in allen Bildern zu sehen ist, andere Gebäude oder Gebäude teile ignorieren.\n"
                "Du antwortest ausschliesslich auf Deutsch und im vorgegebenen JSON-Schema, z.B. 'Dachform: Satteldach', 'Dachmaterial: Ziegel', 'Fenster: 4', 'PV-Anlage: Ja, 20m²'.\n"
            )
        }]

        for p in image_paths:
            content.append({"type": "image_url", "image_url": {"url": image_to_data_url(p)}})

        response = self.client.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                    "Du extrahierst visuelle Gebäudemerkmale aus Bildern.\n"
                    "- Wenn etwas nicht eindeutig sichtbar ist: value_str='UNBEKANNT' oder value_num=None und confidence <= 0.3.\n"
                    "- Nutze nur Merkmale, die visuell plausibel erkennbar sind.\n"
                    "- Fenster: nur erkennen, ob vor 1990 oder ab 1990; sonst UNBEKANNT.\n"
                    "- Fensteranzahl nur schätzen, wenn klar sichtbar; sonst UNBEKANNT.\n"
                    "- Photovoltaik: JA/NEIN/UNBEKANNT. Wenn JA und erkennbar, PV-Fläche schätzen, sonst UNBEKANNT.\n"
                    "- Photovoltaik zählt nicht als Dachbekleidung.\n"
                    "- Fassade_Bekleidung und Dach_Bekleidung sollen die sichtbaren Hauptmaterialien beschreiben.\n"
                    "- WICHTIG: Materialfelder müssen konsistent mit FASSADE_BEKLEIDUNG und DACH_BEKLEIDUNG sein.\n"
                    "- Wenn in FASSADE_BEKLEIDUNG Holz vorkommt, setze HOLZ auf JA.\n"
                    "- Wenn in FASSADE_BEKLEIDUNG Beton vorkommt, setze BETON auf JA.\n"
                    "- Wenn in DACH_BEKLEIDUNG Dachziegel vorkommen, setze DACHZIEGEL auf JA.\n"
                    "- Wenn in DACH_BEKLEIDUNG Stahlblech vorkommt, setze STAHLBLECH auf JA.\n"
                    "- Wenn ein Material klar nicht sichtbar ist, setze es auf NEIN.\n"
                    "- Wenn unklar, setze es auf UNBEKANNT.\n"
                    "- Fassade Dämmung: nur vorsichtig anhand sichtbarer Hinweise schätzen (z. B. Fenstertiefe), sonst UNBEKANNT.\n"
                ),
                },
                {"role": "user", "content": content},
            ],
            response_format=BuildingImageExtraction,
        )

        parsed = response.choices[0].message.parsed
        if isinstance(parsed, BuildingImageExtraction):
            return parsed
        if isinstance(parsed, dict):
            return BuildingImageExtraction(**parsed)
        raise RuntimeError("OpenAI returned unexpected feature format")