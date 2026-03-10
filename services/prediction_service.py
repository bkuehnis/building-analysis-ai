from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier


class CatBoostPredictionService:

    # =========================
    # CONFIG
    # =========================

    def __init__(
        self,
        model_path: str | Path,
        feature_columns: list[str] | None = None,
        cat_features: list[str] | None = None,
    ):
        self.model_path = Path(model_path)
        self.feature_columns = feature_columns
        self.cat_features = cat_features or []
        self.model = CatBoostClassifier()
        self._load_model()

    def _load_model(self) -> None:
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")

        self.model.load_model(str(self.model_path))

    # =========================
    # PREDICTION
    # =========================

    # prepareinput dict to df and remove non-feature columns
    def _prepare_input(self, features: dict[str, Any]) -> pd.DataFrame:
        df = pd.DataFrame([features])
        

        # drop all except required columns + target
        REQUIRED_COLUMNS = [
            "BAUJAHR",
            "TRAGWERK_FASSADE",
            "FASSADE_DAEMMUNG",
            "FASSADE_BEKLEIDUNG",
            "KONSTRUKTION_DACH",
            "DACH_BEKLEIDUNG",
            "PHOTOVOLTAIK",
            "FENSTER"
        ]
        df = df[REQUIRED_COLUMNS].copy()

        #replace nan values to "NAN"
        df = df.fillna("NAN")

        return df

    # predict with confidence score (probability)
    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        df = self._prepare_input(features)

        probabilities = self.model.predict_proba(df)[0]
        classes = self.model.classes_

        best_idx = probabilities.argmax()

        return {
            "prediction": classes[best_idx],
            "confidence": float(probabilities[best_idx]),
            "probabilities": {
                str(cls): float(prob)
                for cls, prob in zip(classes, probabilities)
            }
        }

    