import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Optional

import pandas as pd
from openai import OpenAI
from pydantic import BaseModel, Field


class BuildingAnalysis(BaseModel):
    fassade_bekleidung: str
    fassade_bekleidung_sicherheit: int = Field(ge=0, le=100)

    fassade_daemmung: str
    fassade_daemmung_sicherheit: int = Field(ge=0, le=100)

    konstruktion_dach: str
    konstruktion_dach_sicherheit: int = Field(ge=0, le=100)

    dach_bekleidung: str
    dach_bekleidung_sicherheit: int = Field(ge=0, le=100)

    tragwerk_fassade: str
    tragwerk_fassade_sicherheit: int = Field(ge=0, le=100)

    fenster: str
    fenster_sicherheit: int = Field(ge=0, le=100)

    bodenaufbau: str
    bodenaufbau_sicherheit: int = Field(ge=0, le=100)

    konstruktion_decke: str
    konstruktion_decke_sicherheit: int = Field(ge=0, le=100)

    schadstoff: str
    schadstoff_sicherheit: int = Field(ge=0, le=100)

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

        image_paths = sorted(image_dir.glob(f"*.jpeg"))

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
        image_dir: str | Path = "prediction_model/output/images",
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
- gib einen neuen Wert zurück.
- gib eine Sicherheit von 0-100 zurück, wie sicher du dir mit deiner Einschätzung bist.

Falls ein Attribut anhand der Bilder nicht zuverlässig erkennbar ist, gib trotzdem die beste Einschätzung ab und reduziere die Sicherheit entsprechend.

Gebäudedaten:
{json.dumps(record, ensure_ascii=False, default=str, indent=2)}

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

            analysis = response.output_parsed

            if analysis is None:
                raise ValueError("OpenAI returned no parsed output")

            return analysis.model_dump()

        except Exception as e:

            return {
                    "error": str(e),
                    "llm_predictions": None,
            }
            