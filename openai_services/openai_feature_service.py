import base64
import mimetypes
from typing import List
from openai import OpenAI

from .building_image_schema import BuildingImageExtraction


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
                "Antworte ausschliesslich im vorgegebenen JSON-Schema. Kein Freitext ausserhalb des JSON.\n"
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
                    """
                    Du extrahierst visuelle Gebäudemerkmale aus Bildern.

                        Regeln je Feldobjekt:
                        - value: exakt ein erlaubter Literal-Wert.
                        - confidence: 0.0-1.0.
                        - evidence: kurze deutsche Begründung basierend auf sichtbaren Hinweisen.

                        Bei unklarer Sichtbarkeit:
                        - confidence <= 0.3
                        - passenden Unknown-Wert verwenden.

                        Konsistenzregeln:
                        - Photovoltaik ist keine Dachbekleidung.
                        - Materialfelder müssen zu Fassaden- und Dachbekleidung passen.
                        - Keine erfundenen Informationen."""
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