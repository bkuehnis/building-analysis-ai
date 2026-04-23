import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Optional

import pandas as pd
from openai import OpenAI
from pydantic import BaseModel, Field

from .building_image_schema import (
    FieldEstimate,
    FassadeBekleidungLiteral,
    FassadeDaemmungLiteral,
    KonstruktionDachLiteral,
    DachBekleidungLiteral,
    TragwerkFassadeLiteral,
    FensterLiteral,
    BodenaufbauLiteral,
    KonstruktionDeckeLiteral,
    SchadstoffLiteral,
)


class BuildingAnalysis(BaseModel):
    fassade_bekleidung: FieldEstimate[FassadeBekleidungLiteral]
    fassade_daemmung: FieldEstimate[FassadeDaemmungLiteral]
    konstruktion_dach: FieldEstimate[KonstruktionDachLiteral]
    dach_bekleidung: FieldEstimate[DachBekleidungLiteral]
    tragwerk_fassade: FieldEstimate[TragwerkFassadeLiteral]
    fenster: FieldEstimate[FensterLiteral]
    bodenaufbau: FieldEstimate[BodenaufbauLiteral]
    konstruktion_decke: FieldEstimate[KonstruktionDeckeLiteral]
    schadstoff: FieldEstimate[SchadstoffLiteral]

    begruendung: Optional[str] = None


class AdditionalPredictionOpenAI:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    @staticmethod
    def image_to_data_url(path: str | Path) -> str:
        path = str(path)
        mime_type, _ = mimetypes.guess_type(path)

        if mime_type is None:
            mime_type = "image/jpeg"

        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        return f"data:{mime_type};base64,{b64}"

    @staticmethod
    def load_image_paths_for_egid(
        egid: str | int,
        image_dir: str | Path,
    ) -> list[str]:
        egid = str(egid)
        image_dir = Path(image_dir) / egid

        image_paths = sorted(image_dir.glob("*.jpeg"))

        if not image_paths:
            raise FileNotFoundError(
                f"No images found for EGID {egid} in {image_dir}"
            )

        return [str(p) for p in image_paths]

    def analyze(
        self,
        df: pd.DataFrame,
        predictions: dict,
        image_paths: Optional[list[str]] = None,
        egid: Optional[str | int] = None,
        image_dir: str | Path = "buildings",
    ):
        print("Starting analysis with AdditionalPredictionOpenAI...")
        print("EGID:", egid)

        if df is None or df.empty:
            raise ValueError("Input DataFrame is empty")

        record = df.iloc[0].to_dict()

        if image_paths is None:
            if egid is None:
                egid = record.get("EGID")

            if egid is None:
                raise ValueError("No EGID found in df and no egid argument was provided")

            image_paths = self.load_image_paths_for_egid(
                egid=egid,
                image_dir=image_dir,
            )

        image_paths = [str(p) for p in image_paths]

        if not image_paths:
            raise ValueError("No image paths provided for analysis")

        print("Loaded image paths:", image_paths)
        print("Number of images:", len(image_paths))

        prompt = f"""
Analysiere die folgenden Bilder eines Hauses sowie die Gebäudedaten und die bereits vorhandenen Einschätzungen.

Gib eigene Einschätzung zu folgenden Attributen ab:
- fassade_bekleidung
- konstruktion_dach
- dach_bekleidung
- tragwerk_fassade
- fassade_daemmung
- fenster (Art und ob vor oder nach 1990 eingebaut)
- bodenaufbau
- konstruktion_decke
- schadstoff (z.B. Asbest, PCB, Holzschutzmittel)

Für jedes Attribut:
- gib exakt einen erlaubten Wert zurück.
- gib confidence als Zahl zwischen 0.0 und 1.0 zurück.

Falls ein Attribut anhand der Bilder nicht zuverlässig erkennbar ist, verwende den passenden Unknown-/Unklar-Wert und reduziere die confidence entsprechend.

Gebäudedaten:
{json.dumps(record, ensure_ascii=False, default=str, indent=2)}

Vorhersagen:
{json.dumps(predictions, ensure_ascii=False, default=str, indent=2)}
""".strip()

        content = [{"type": "input_text", "text": prompt}]

        for p in image_paths:
            content.append(
                {
                    "type": "input_image",
                    "image_url": self.image_to_data_url(p),
                }
            )

        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {
                        "role": "user",
                        "content": content,
                    }
                ],
                text_format=BuildingAnalysis,
            )

            analysis = getattr(response, "output_parsed", None)

            if analysis is None:
                # SDK compatibility fallback
                output = getattr(response, "output", None) or []
                if output:
                    content_items = getattr(output[0], "content", None) or []
                    if content_items:
                        analysis = getattr(content_items[0], "parsed", None)

            if analysis is None:
                raise ValueError("OpenAI returned no parsed output")

            # Pydantic -> dict
            raw = analysis.model_dump()

            # In altes flaches Format umwandeln
            flat = {}
            for key, value in raw.items():
                if key == "begruendung":
                    flat[key] = value
                    continue

                if isinstance(value, dict):
                    flat[key] = value.get("value")
                    confidence = value.get("confidence")
                    flat[f"{key}_sicherheit"] = round(confidence * 100) if confidence is not None else None
                else:
                    flat[key] = value

            return flat

        except Exception as e:
            return {
                "error": str(e),
                "llm_predictions": None,
            }