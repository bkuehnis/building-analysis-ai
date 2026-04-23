from typing import Generic, List, Literal, TypeVar
from pydantic import BaseModel, Field, computed_field

T = TypeVar("T", bound=str)

YesNoUnklar = Literal["JA", "NEIN", "UNKLAR", "UNBEKANNT"]

SchadstoffLiteral = Literal[
    "JA",
    "NEIN",
    "HOHE CHANCE",
    "NIEDRIG CHANCE",
    "H.W. ASBEST, PCB, PAK",
    "H. W. HOLZSCHUTZMITTEL",
    "UNBEKANNT",
]

TragwerkFassadeLiteral = Literal[
    "MASSIV HOLZ",
    "PUNKTUELL HOLZ",
    "MASSIV GEDAEMMT HOLZ",
    "PUNKTUELL STAHL",
    "MASSIV BACKSTEIN",
    "MASSIV BETON",
    "PUNKTUELL BETON MIT BACKSTEINWAENDE",
    "PUNKTUELL BETON MIT HOLZFASSADE",
    "DAMMBETON",
    "MASSIVBAU",
    "LEICHTBAU",
    "UNBEKANNT",
]

FassadeDaemmungLiteral = Literal[
    "KEIN",
    "XPS ODER GEKLEBTE LEICHTE DAEMMUNG",
    "MINERALDAEMMUNG ODER LEICHTE DAEMMUNG",
    "UNBEKANNT",
]

FassadeBekleidungLiteral = Literal[
    "LEICHTBAU HOLZPLATTEN, MIT UNTERKONSTRUKTION",
    "LEICHTBAU HOLZSCHINDEL, MIT UNTERKONSTRUKTION",
    "MASSIV BETON MIT HINTERLUEFTUNG",
    "MASSIV BACKSTEIN MIT HINTERLUEFTUNG",
    "MASSIV BETON PREFAB MIT HINTERLUEFTUNG",
    "LEICHTBAU STAHLBLECH",
    "LEICHTBAU GLASFASERNPLATTE",
    "LEICHTBAU STEIN",
    "LEICHTBAU ANDERE LEICHTMATERIALIEN",
    "PUTZ",
    "DAEMMBETON",
    "UNBEKANNT",
]

KonstruktionDeckeLiteral = Literal[
    "LEICHTBAU HOLZ MIT HOLZDECKE",
    "LEICHTBAU STAHL MIT HOLLRIPDECKEN",
    "LEICHTBAU STAHL MIT HOLZDECKE",
    "KEINE",
    "BETON KONVENTIONELL",
    "BACKSTEINPLATTENDECKE",
    "UNBEKANNT",
]

BodenaufbauLiteral = Literal[
    "KONVENTIONELLER MIT BH",
    "KONVENTIONELLER OHNE BH",
    "UNBEKANNT",
]

KonstruktionDachLiteral = Literal[
    "STEILDACH, HOLZKONSTRUKTION",
    "STEILDACH, BETONKONSTRUKTION",
    "STEILDACH, BACKSTEINPLATTENDECKE",
    "STEILDACH, STAHLKONSTRUKTION",
    "SCHEDDACH HOLZ",
    "SCHEDDACH STAHL",
    "SCHEDDACH BETON",
    "SCHEDDACH BACKSTEINPLATTENDECKE",
    "FLACHDACH HOLZKONSTRUKTION",
    "FLACHDACH STAHLKONSTRUKTION",
    "FLACHDACH BETONKONSTRUKTION",
    "UNBEKANNT",
]

DachBekleidungLiteral = Literal[
    "HOLZSCHINDEL",
    "ZIEGEL",
    "STAHLBLECH",
    "FLACHDACH UNGEDAEMMT",
    "FLACHDACH GEDAEMMT",
    "FLACHDACH GRUEN GEDAEMMT",
    "UNBEKANNT",
]

PhotovoltaikLiteral = Literal["JA", "NEIN", "UNKLAR", "UNBEKANNT"]
FensterLiteral = Literal["AB 1990", "BEVOR 1990", "KEIN", "UNKLAR", "UNBEKANNT"]


class FieldEstimate(BaseModel, Generic[T]):
    value: T
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str

    @computed_field(return_type=float)
    @property
    def confidence_pct(self) -> float:
        return round(self.confidence * 100.0, 1)


class BuildingImageExtraction(BaseModel):
    # Schritt 1: Sichtbare Merkmale
    fassade_bekleidung: FieldEstimate[FassadeBekleidungLiteral]
    konstruktion_dach: FieldEstimate[KonstruktionDachLiteral]
    dach_bekleidung: FieldEstimate[DachBekleidungLiteral]
    photovoltaik: FieldEstimate[PhotovoltaikLiteral]
    fenster: FieldEstimate[FensterLiteral]

    # Sichtbare Materialien
    holz: FieldEstimate[YesNoUnklar]
    beton: FieldEstimate[YesNoUnklar]
    stahl: FieldEstimate[YesNoUnklar]
    stahlblech: FieldEstimate[YesNoUnklar]
    eternit: FieldEstimate[YesNoUnklar]
    steinplatten: FieldEstimate[YesNoUnklar]
    dachziegel: FieldEstimate[YesNoUnklar]

    # optional fuer andere Auffaelligkeiten
    speziell: FieldEstimate[YesNoUnklar]
    extra: FieldEstimate[YesNoUnklar]

    @computed_field(return_type=float)
    @property
    def overall_confidence_pct(self) -> float:
        confidences = [
            value.confidence
            for value in self.__dict__.values()
            if isinstance(value, FieldEstimate)
        ]
        if not confidences:
            return 0.0
        return round(sum(confidences) / len(confidences) * 100.0, 1)
    
class AnalysisReasoningItem(BaseModel):
    attribute: str
    assessment: str
    reason: str


class AnalysisUncertaintyItem(BaseModel):
    attribute: str
    reason: str


class BuildingAnalysisResult(BaseModel):
    summary: str
    reasoning: List[AnalysisReasoningItem]
    uncertainty: List[AnalysisUncertaintyItem]
