from pydantic import BaseModel, Field
from typing import Optional, Literal

Material = Literal[
    "FLACHDACH UNGEDÄMMT",
    "FLACHDACH GEDÄMMT",
    "FLACHDACH UNBEKANNT",
    "ETERNIT",
    "ZIEGEL",
    "STAHLBLECH",
    "STAHL",
    "STEINPLATTEN",
    "BETON",
    "HOLZSCHINDEL",
    "HOLZ",
    "SCHIEFER",
    "SPEZIELL",
    "UNBEKANNT",
    
]



YesNoUnk = Literal["JA", "NEIN", "NA"]

class FieldEstimate(BaseModel):
    value_str: Optional[str] = None
    value_num: Optional[float] = None
    unit: Optional[Literal["m2", "lm", "count"]] = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Optional[str] = None

class BuildingImageExtraction(BaseModel):
    # Fassaden / Außenhaut
    tragwerk_fassade: FieldEstimate
    fassade_daemmung: FieldEstimate
    fassade_bekleidung: FieldEstimate
    fenster: FieldEstimate
    fensteranzahl: FieldEstimate
    daemmungsflaeche: FieldEstimate

    # Dach
    konstruktion_dach: FieldEstimate
    dach_bekleidung: FieldEstimate
    photovoltaik: FieldEstimate
    pv_flaeche: FieldEstimate

    # Konstruktion (meist nicht sichtbar)
    konstruktion_decke: FieldEstimate
    bodenaufbau: FieldEstimate

    # Material-/Mengenblöcke
    stahl: FieldEstimate
    stahl_lm: FieldEstimate
    stahlblech: FieldEstimate
    stahlblech_flaeche: FieldEstimate

    eternit: FieldEstimate
    eternit_flaeche: FieldEstimate
    steinplatten: FieldEstimate
    steinplatten_flaeche: FieldEstimate
    dachziegel: FieldEstimate
    dachziegel_flaeche: FieldEstimate
    beton: FieldEstimate
    beton_flaeche: FieldEstimate
    holz: FieldEstimate
    holz_lm: FieldEstimate
    holz_flaeche: FieldEstimate

    speziell: FieldEstimate
    speziell_flaeche: FieldEstimate
    extra: FieldEstimate