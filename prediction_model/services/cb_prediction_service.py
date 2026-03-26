from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier


class CatBoostFoldEnsemble:
    def __init__(self, model_dir, feature_columns, categorical_cols=None):
        self.model_dir = Path(model_dir)
        self.feature_columns = feature_columns
        self.categorical_cols = categorical_cols or []
        self.models = self._load_models()
        self.classes_ = np.array(self.models[0].classes_)

    def _load_models(self):
        fold_dir = self.model_dir / "folds"
        model_paths = sorted(fold_dir.glob("catboost_fold_*.cbm"))
        if not model_paths:
            raise FileNotFoundError(f"Keine CatBoost-Fold-Modelle gefunden in {fold_dir}")

        models = []
        for path in model_paths:
            model = CatBoostClassifier()
            model.load_model(str(path))
            models.append(model)

        return models

    def _prepare_input(self, X_new: pd.DataFrame) -> pd.DataFrame:
        X = X_new.copy()

        # exakt die erwarteten Spalten
        X = X.reindex(columns=self.feature_columns)

        for col in self.feature_columns:
            if col in self.categorical_cols:
                X[col] = X[col].fillna("UNBEKANNT").astype(str)
            else:
                X[col] = pd.to_numeric(X[col], errors="coerce")

        return X

    def predict_proba(self, X_new: pd.DataFrame) -> np.ndarray:
        X_prepared = self._prepare_input(X_new)

        probas = np.array([model.predict_proba(X_prepared) for model in self.models])
        mean_probas = probas.mean(axis=0)

        return mean_probas

    def predict(self, X_new: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        mean_probas = self.predict_proba(X_new)
        class_indices = np.argmax(mean_probas, axis=1)

        predictions = self.classes_[class_indices]
        confidences = mean_probas.max(axis=1)

        return predictions, confidences