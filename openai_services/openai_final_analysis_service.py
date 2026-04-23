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


    def analyze(self, comparison_df: pd.DataFrame, predictions: dict) -> dict:
        if comparison_df.empty:
            raise ValueError("comparison_df is missing imputable data for analysis.")
       
        prompt = f"""
        Du bist ein Experte für die Einschätzung von Gebäudemerkmalen.

        Analysiere die folgenden Gebäudedaten und Modellvorhersagen.

        Regeln:
        - Begründe jede Aussage ausschließlich mit den gegebenen Daten und Vorhersagen.
        - Nutze die Confidence-Werte explizit zur Einordnung der Zuverlässigkeit.
        - Formuliere vorsichtig und vermeide absolute Aussagen.
        - Wenn Daten oder Vorhersagen unsicher, unvollständig oder widersprüchlich sind, benenne dies ausdrücklich.
        - Erfinde keine zusätzlichen Merkmale, Zustände oder Empfehlungen.
        - Gib keine Informationen wieder, die nicht aus den Eingabedaten ableitbar sind.

        Ziel:
        - Fasse die wichtigsten Merkmale des Gebäudes kurz zusammen.
        - Erkläre, welche Vorhersagen plausibel erscheinen und warum (confidence > 80).
        - Erkläre, welche Vorhersagen stark unsicher sind und warum (confidence <= 40).

        Gebäudedaten:
        {json.dumps(comparison_df.to_dict, ensure_ascii=False, default=str, indent=2)}

        Vorhersagen:
        {json.dumps(predictions, ensure_ascii=False, default=str, indent=2)}

        Gib ausschließlich gültiges JSON zurück, ohne zusätzlichen Text. Konfidenz nennst du "Sicherheit"

        Format:
        {{
        "summary": "...",
        "reasoning": [
            {{
            "attribute": "...",
            "assessment": "...",
            "reason": "..."
            }}
        ],
        "uncertainty": [
            {{
            "attribute": "...",
            "reason": "..."
            }}
        ]
        }}
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        text = response.choices[0].message.content

        try:
            return json.loads(text)
        except Exception:
            return {"summary": text}