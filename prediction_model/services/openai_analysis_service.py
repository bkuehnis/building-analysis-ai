from __future__ import annotations
from openai import OpenAI
import pandas as pd
import json
import os
from dotenv import load_dotenv


class OpenAIAnalysisService:

    load_dotenv()

    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")

        self.client = OpenAI(api_key=api_key)
        self.model = model


    def analyze(self, df: pd.DataFrame, predictions: dict) -> dict:
        record = df.iloc[0].to_dict()

        prompt = f"""
    Du bist ein Experte für Gebäudebewertung.

    Analysiere die folgenden Gebäudedaten und Modellvorhersagen in minimalistischer Form.

    Wichtig:
    - Begründe deine Einschätzung nur mit den gegebenen Daten
    - Weise auf Unsicherheiten hin
    - Keine absoluten Aussagen
    - Keine Halluzinationen

    Gebäudedaten:
    {json.dumps(record, ensure_ascii=False, default=str, indent=2)}

    Vorhersagen:
    {json.dumps(predictions, ensure_ascii=False, default=str, indent=2)}

    Gib die Antwort als JSON zurück mit:
    - summary (kurze Zusammenfassung)
    - reasoning (Liste von Gründen)
    - uncertainty (Unsicherheiten)
    - recommendation (Empfehlung)
    """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.choices[0].message.content

        try:
            return json.loads(text)
        except Exception:
            return {"summary": text}