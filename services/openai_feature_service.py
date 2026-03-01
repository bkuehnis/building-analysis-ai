import base64
from typing import List
from openai import OpenAI

from models.building_image_schema import BuildingImageExtraction


def image_to_data_url(path: str) -> str:
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


class OpenAIFeatureService:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract_features(self, image_paths: List[str]) -> BuildingImageExtraction:
        content = [{
            "type": "text",
            "text": (
                "Extrahiere Gebäude-Features aus den folgenden Bildern. "
                "Nutze beide Perspektiven gemeinsam (Fassade + Dach)."
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
                        "Du antwortest nur mit deutschen Bergriffen, z.B. 'Dachform: Satteldach', 'Dachmaterial: Ziegel', 'Fenster: 4', 'PV-Anlage: Ja, 20m²'.\n"
                        "- Wenn nicht eindeutig sichtbar: value_str='unknown' oder value_num=None und confidence <= 0.3.\n"
                        "- Keine Konstruktionen raten (Decke/Bodenaufbau/Tragwerk), nur wenn sichtbar.\n"
                        "- Flächen nur schätzen, wenn Massstab oder klare Geometrie erkennbar, sonst value_num=None.\n"
                        "- Fenster: Anzahl nur schätzen wenn sichtbar; sonst unknown/None.\n"
                        "- Photovoltaik: JA/NEIN/NA; wenn JA und erkennbar, PV-Fläche schätzen, sonst NA.\n"
                        "- Photovoltaik zählt nicht als Dachbekleidung\n"
                        "Antworte strikt im vorgegebenen JSON-Schema."
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