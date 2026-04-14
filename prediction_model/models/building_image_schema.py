from pydantic import BaseModel, Field
from typing import Optional, Literal

YesNoUnk = Literal["JA", "NEIN", "NA"]

class FieldEstimate(BaseModel):
    value_str: Optional[str] = None
    value_enum: Optional[YesNoUnk] = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Optional[str] = None

class BuildingImageExtraction(BaseModel):
    # Grobe visuelle Gebäudeattribute
    fassade_bekleidung: FieldEstimate
    fenster: FieldEstimate
    dach_bekleidung: FieldEstimate
    photovoltaik: FieldEstimate

    # Sichtbare Materialien
    holz: FieldEstimate
    beton: FieldEstimate
    stahl: FieldEstimate
    stahlblech: FieldEstimate
    eternit: FieldEstimate
    steinplatten: FieldEstimate
    dachziegel: FieldEstimate

    # optional für andere auffälligkeiten
    speziell: FieldEstimate
    extra: FieldEstimate