"""
Combined Prediction Service for integrating CatBoost and RandomForest models.

to run in terminal with input data:
python -c "import pandas as pd; from prediction_model.services.combined_prediction_service import CombinedFoldEnsemble; model = CombinedFoldEnsemble(model_dir='prediction_model/models/schadstoff/saved_models'); X_new = pd.DataFrame([{'BAUJAHR': 1990, 'TRAGWERK_FASSADE': 'Mauerwerk', 'FASSADE_DAEMMUNG': 'Keine', 'FASSADE_BEKLEIDUNG': 'Keine', 'KONSTRUKTION_DACH': 'Satteldach', 'DACH_BEKLEIDUNG': 'Ziegel', 'PHOTOVOLTAIK': 'Nein', 'FENSTER': 'ab_1990'}]); result = model.predict(X_new); print(result)" 
-> also add prediction_model. in front of service
and for MyApp remove "prediction_model." from the import statement
"""
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

from prediction_model.services.cb_prediction_service import CatBoostFoldEnsemble
from prediction_model.services.rf_prediction_service import RandomForestFoldEnsemble

FEATURE_COLUMNS_FASSADEN_BEKLEIDUNG = [
    "BAUJAHR",
    "HOLZ",
    "STAHL",
    "STAHLBLECH",
    "BETON",
]
CATEGORICAL_COLUMNS_FASSADEN_BEKLEIDUNG = [
    "HOLZ",
    "STAHL",
    "STAHLBLECH",
    "BETON",
]

FEATURE_COLUMNS_DACH_BEKLEIDUNG = [
    "BAUJAHR",
    "KONSTRUKTION_DACH",
    "HOLZ",
    "STAHL",
    "STAHLBLECH",
    "BETON",
]
CATEGORICAL_COLUMNS_DACH_BEKLEIDUNG = [
    "KONSTRUKTION_DACH",
    "HOLZ",
    "STAHL",
    "STAHLBLECH",
    "BETON",
]

FEATURE_COLUMNS_KONSTRUKTION_DACH = [
    "BAUJAHR",
    "HOLZ",
    "STAHL",
    "STAHLBLECH",
    "BETON",
]
CATEGORICAL_COLUMNS_KONSTRUKTION_DACH = [
    "HOLZ",
    "STAHL",
    "STAHLBLECH",
    "BETON",
]

FEATURE_COLUMNS_TRAGWERK_FASSADE = [
    "BAUJAHR",
    "HOLZ",
    "STAHL",
    "STAHLBLECH",
    "BETON",
    "HAUPTNUTZUNG",
    "FASSADE_BEKLEIDUNG",
    "KONSTRUKTION_DACH",
]
CATEGORICAL_COLUMNS_TRAGWERK_FASSADE = [
    "HOLZ",
    "STAHL",
    "STAHLBLECH",
    "BETON",
    "HAUPTNUTZUNG",
    "FASSADE_BEKLEIDUNG",
    "KONSTRUKTION_DACH",
]

FEATURE_COLUMNS_FASSADEN_DAEMMUNG = [
    "BAUJAHR",
    "TRAGWERK_FASSADE",
    "FASSADE_BEKLEIDUNG",
    "DACH_BEKLEIDUNG",
    "KONSTRUKTION_DACH",
    "HAUPTNUTZUNG",
]
CATEGORICAL_COLUMNS_FASSADEN_DAEMMUNG = [
    "TRAGWERK_FASSADE",
    "FASSADE_BEKLEIDUNG",
    "DACH_BEKLEIDUNG",
    "KONSTRUKTION_DACH",
    "HAUPTNUTZUNG",
]

FEATURE_COLUMNS_FENSTER = [
    "BAUJAHR",
    "TRAGWERK_FASSADE",
    "FASSADE_DAEMMUNG",
]
CATEGORICAL_COLUMNS_FENSTER = [
    "TRAGWERK_FASSADE",
    "FASSADE_DAEMMUNG",
]

FEATURE_COLUMNS_BODENAUFBAU = [
    "BAUJAHR",
    "TRAGWERK_FASSADE",
    "FASSADE_BEKLEIDUNG",
    "FASSADE_DAEMMUNG",
    "HAUPTNUTZUNG",
    "FENSTER",
]
CATEGORICAL_COLUMNS_BODENAUFBAU = [
    "TRAGWERK_FASSADE",
    "FASSADE_BEKLEIDUNG",
    "FASSADE_DAEMMUNG",
    "HAUPTNUTZUNG",
    "FENSTER",
]

FEATURE_COLUMNS_KONSTRUKTION_DECKE = [
    "BAUJAHR",
    "TRAGWERK_FASSADE",
    "DACH_BEKLEIDUNG",
    "HOLZ",
    "STAHL",
    "STAHLBLECH",
    "BETON",
    "HAUPTNUTZUNG",
    "FENSTER",
]
CATEGORICAL_COLUMNS_KONSTRUKTION_DECKE = [
    "TRAGWERK_FASSADE",
    "DACH_BEKLEIDUNG",
    "HOLZ",
    "STAHL",
    "STAHLBLECH",
    "BETON",
    "HAUPTNUTZUNG",
    "FENSTER",
]

FEATURE_COLUMNS_SCHADSTOFFE = [
    "BAUJAHR",
    "TRAGWERK_FASSADE",
    "FASSADE_DAEMMUNG",
    "FASSADE_BEKLEIDUNG",
    "KONSTRUKTION_DACH",
    "DACH_BEKLEIDUNG",
    "PHOTOVOLTAIK",
    "FENSTER"
]
CATEGORICAL_COLUMNS_SCHADSTOFFE = [
    "TRAGWERK_FASSADE",
    "FASSADE_DAEMMUNG",
    "FASSADE_BEKLEIDUNG",
    "KONSTRUKTION_DACH",
    "DACH_BEKLEIDUNG",
    "PHOTOVOLTAIK",
    "FENSTER"
]


class CombinedFoldEnsemble:
    def __init__(
        self,
        model_dir: str | Path,
        feature_columns: list[str] | None = None,
        required_columns: list[str] | None = None,
        categorical_cols: list[str] | None = None,
    ):
        self.model_dir = Path(model_dir)

        if feature_columns is None:
            feature_columns = self._load_feature_columns_cb(self.model_dir)

        if categorical_cols is None:
            categorical_cols = self._load_categorical_columns_cb(self.model_dir)

        if required_columns is None:
            required_columns = self._load_required_columns_rf(self.model_dir)

        self.cb_model = CatBoostFoldEnsemble(
            model_dir=self.model_dir,
            feature_columns=feature_columns,
            categorical_cols=categorical_cols,
        )

        self.rf_model = RandomForestFoldEnsemble(
            model_dir=self.model_dir,
            required_columns=required_columns,
        )

        if list(self.cb_model.classes_) != list(self.rf_model.classes_):
            raise ValueError("Class order mismatch between CatBoost and RandomForest.")

        self.classes_ = self.cb_model.classes_

        print("CombinedFoldEnsemble initialized with:")
        print(f"Model Dir: {self.model_dir}")

    def _load_categorical_columns_cb(self, model_dir: Path) -> list[str]:
        if "fassade_bekleidung" in str(model_dir):
            return CATEGORICAL_COLUMNS_FASSADEN_BEKLEIDUNG
        if "dach_bekleidung" in str(model_dir):
            return CATEGORICAL_COLUMNS_DACH_BEKLEIDUNG
        if "konstruktion_dach" in str(model_dir):
            return CATEGORICAL_COLUMNS_KONSTRUKTION_DACH
        if "tragwerk_fassade" in str(model_dir):
            return CATEGORICAL_COLUMNS_TRAGWERK_FASSADE
        if "fassade_daemmung" in str(model_dir):
            return CATEGORICAL_COLUMNS_FASSADEN_DAEMMUNG
        if "fenster" in str(model_dir):
            return CATEGORICAL_COLUMNS_FENSTER
        if "bodenaufbau" in str(model_dir):
            return CATEGORICAL_COLUMNS_BODENAUFBAU
        if "konstruktion_decke" in str(model_dir):
            return CATEGORICAL_COLUMNS_KONSTRUKTION_DECKE
        if "schadstoff" in str(model_dir):
            return CATEGORICAL_COLUMNS_SCHADSTOFFE
        raise ValueError(f"No default categorical columns configured for model_dir={model_dir}")

    def _load_feature_columns_cb(self, model_dir: Path) -> list[str]:
        if "fassade_bekleidung" in str(model_dir):
            return FEATURE_COLUMNS_FASSADEN_BEKLEIDUNG
        if "dach_bekleidung" in str(model_dir):
            return FEATURE_COLUMNS_DACH_BEKLEIDUNG
        if "konstruktion_dach" in str(model_dir):
            return FEATURE_COLUMNS_KONSTRUKTION_DACH
        if "tragwerk_fassade" in str(model_dir):
            return FEATURE_COLUMNS_TRAGWERK_FASSADE
        if "fassade_daemmung" in str(model_dir):
            return FEATURE_COLUMNS_FASSADEN_DAEMMUNG
        if "fenster" in str(model_dir):
            return FEATURE_COLUMNS_FENSTER
        if "bodenaufbau" in str(model_dir):
            return FEATURE_COLUMNS_BODENAUFBAU
        if "konstruktion_decke" in str(model_dir):
            return FEATURE_COLUMNS_KONSTRUKTION_DECKE
        if "schadstoff" in str(model_dir):
            return FEATURE_COLUMNS_SCHADSTOFFE
        raise ValueError(f"No default feature columns configured for model_dir={model_dir}")

    def _load_required_columns_rf(self, model_dir: Path) -> list[str]:
        if "fassade_bekleidung" in str(model_dir):
            return FEATURE_COLUMNS_FASSADEN_BEKLEIDUNG
        if "dach_bekleidung" in str(model_dir):
            return FEATURE_COLUMNS_DACH_BEKLEIDUNG
        if "konstruktion_dach" in str(model_dir):
            return FEATURE_COLUMNS_KONSTRUKTION_DACH
        if "tragwerk_fassade" in str(model_dir):
            return FEATURE_COLUMNS_TRAGWERK_FASSADE
        if "fassade_daemmung" in str(model_dir):
            return FEATURE_COLUMNS_FASSADEN_DAEMMUNG
        if "fenster" in str(model_dir):
            return FEATURE_COLUMNS_FENSTER
        if "bodenaufbau" in str(model_dir):
            return FEATURE_COLUMNS_BODENAUFBAU
        if "konstruktion_decke" in str(model_dir):
            return FEATURE_COLUMNS_KONSTRUKTION_DECKE
        if "schadstoff" in str(model_dir):
            return FEATURE_COLUMNS_SCHADSTOFFE
        raise ValueError(f"No default required columns configured for model_dir={model_dir}")

    def predict_proba(self, X_new: pd.DataFrame) -> np.ndarray:
        cb_probas = self.cb_model.predict_proba(X_new)
        rf_probas = self.rf_model.predict_proba(X_new)

        # Align RF classes to CB
        rf_probas = rf_probas[:, [
            list(self.rf_model.classes_).index(cls)
            for cls in self.cb_model.classes_
        ]]

        mean_probas = (cb_probas + rf_probas) / 2
        """
        # Weighted average (says GPT)
        mean_probas = 0.6 * cb_probas + 0.4 * rf_probas
        """

        print("CombinedFoldEnsemble predict_proba:")
        print(f"CatBoost Probabilities: {cb_probas}")
        print(f"RandomForest Probabilities: {rf_probas}")
        print(f"Mean Probabilities: {mean_probas}")
        return mean_probas

    def predict(self, X_new: pd.DataFrame) -> dict[str, np.ndarray]:
        mean_probas = self.predict_proba(X_new)
        class_indices = np.argmax(mean_probas, axis=1)

        predictions = self.classes_[class_indices]
        confidences = mean_probas.max(axis=1)
        model_name = self.model_dir.parent.name 


        print("CombinedFoldEnsemble prediction:")
        print(f"Predictions: {predictions}")
        print(f"Confidences: {confidences}")
        print(f"Probabilities: {mean_probas}")

        return {
            "prediction": predictions,
            "confidence": confidences,
            "probabilities": mean_probas,
            "model_name": model_name
        }