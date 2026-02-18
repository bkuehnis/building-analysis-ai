#!/usr/bin/env python3
"""Compare extracted Werk-material fields with the true Excel values and score similarity."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

# Base paths
BASE_DIR = Path(__file__).parent.parent

SOURCES = [
    ("text", "_text.json"),
    ("images", "_images.json"),
    ("combined", "_images_text.json"),
]

FIELDS = [
    "Jahr (Fertigstellung)",
    "Ort",
    "Architekt",
    "Dach",
    "Aussenwand",
    "Fenster",
    "Tragwerk",
    "Decke",
    "Innenwände",
    "Haustechnik",
]

FIELD_KEY_ALIASES: Dict[str, List[str]] = {
    "Jahr (Fertigstellung)": ["Jahr (Fertigstellung)", "jahr_fertigstellung"],
    "Ort": ["Ort", "ort"],
    "Architekt": ["Architekt", "architekt"],
    "Dach": ["Dach", "dach"],
    "Aussenwand": ["Aussenwand", "Aussenwand".lower()],
    "Fenster": ["Fenster", "fenster"],
    "Tragwerk": ["Tragwerk", "tragwerk"],
    "Decke": ["Decke", "decke"],
    "Innenwände": ["Innenwände", "Innenwaende", "innenwaende", "innenwände"],
    "Haustechnik": ["Haustechnik", "haustechnik"],
}


class FieldComparison(BaseModel):
    field: str
    truth: Optional[str] = None
    extracted: Optional[str] = None
    score: Optional[float] = None
    similar: Optional[bool] = None
    comment: Optional[str] = None


class EvaluationResult(BaseModel):
    comparisons: List[FieldComparison]


@dataclass
class CsvRow:
    source: str
    building_id: str
    field: str
    truth: Optional[str]
    extracted: Optional[str]
    score: Optional[float]
    similar: Optional[bool]
    comment: Optional[str]


def normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip('"')).lower()


def find_column(columns: List[str], target: str) -> Optional[str]:
    target_norm = normalize_header(target)
    for column in columns:
        if normalize_header(column) == target_norm:
            return column
    return None


def read_truth(excel_path: Path) -> Dict[str, Dict[str, Optional[str]]]:
    df = pd.read_excel(excel_path, dtype=str)
    df.columns = [str(c) for c in df.columns]

    id_column = find_column(df.columns.tolist(), "werk.material")
    if not id_column:
        raise SystemExit("Could not find 'werk.material' column in truth file")

    truth_map: Dict[str, Dict[str, Optional[str]]] = {}
    for _, row in df.iterrows():
        raw_id = row[id_column]
        if pd.isna(raw_id):
            continue
        building_id = str(raw_id).strip()
        if not building_id:
            continue
        entry: Dict[str, Optional[str]] = {}
        for field in FIELDS:
            column = find_column(df.columns.tolist(), field)
            value = str(row[column]).strip() if column and not pd.isna(row[column]) else None
            entry[field] = value
        truth_map[building_id] = entry
    return truth_map


def canonicalize_extracted(raw: Dict[str, Any]) -> Dict[str, Optional[str]]:
    normalized: Dict[str, Optional[str]] = {}
    for field, aliases in FIELD_KEY_ALIASES.items():
        normalized[field] = None
        for alias in aliases:
            if alias in raw:
                normalized[field] = raw[alias]
                break
    return normalized


def load_extraction(directory: Path, building_id: str, suffix: str) -> Dict[str, Optional[str]]:
    path = directory / f"{building_id}{suffix}"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return canonicalize_extracted(payload)


def heuristic_score(truth: Optional[str], extracted: Optional[str]) -> float:
    if not truth or not extracted:
        return 0.0
    matcher = SequenceMatcher(None, truth.lower(), extracted.lower())
    return matcher.ratio() * 100


def create_heuristic_result(
    building_id: str,
    truth: Dict[str, Optional[str]],
    extracted: Dict[str, Optional[str]],
) -> EvaluationResult:
    comparisons: List[FieldComparison] = []
    for field in FIELDS:
        truth_value = truth.get(field)
        extracted_value = extracted.get(field)
        score = heuristic_score(truth_value, extracted_value)
        comparisons.append(
            FieldComparison(
                field=field,
                truth=truth_value,
                extracted=extracted_value,
                score=round(score, 2),
                similar=score >= 80,
                comment="heuristic (dry-run or fallback)",
            )
        )
    return EvaluationResult(comparisons=comparisons)


def evaluate_with_openai(
    api_key: str,
    model: str,
    truth: Dict[str, Optional[str]],
    extracted: Dict[str, Optional[str]],
) -> EvaluationResult:
    client = OpenAI(api_key=api_key)
    truth_payload = {field: truth.get(field) for field in FIELDS}
    extracted_payload = {field: extracted.get(field) for field in FIELDS}
    messages = [
        {
            "role": "system",
            "content": (
                "Du bewertest, wie ähnlich die extrahierten Felder den wahren Werten sind. "
                "Jedes Feld bekommt einen Score zwischen 0 und 100, sowie eine boolesche Angabe 'similar'."
                "Antwort als JSON mit 'comparisons'."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Wahrheitswerte: {json.dumps(truth_payload, ensure_ascii=False)}\n"
                f"Extraktion: {json.dumps(extracted_payload, ensure_ascii=False)}\n"
                "Gib für jedes Feld ein Objekt mit 'field', 'truth', 'extracted', 'score', 'similar', 'comment'."
                " 'score' 0-100, 'similar' true wenn Score >= 70."
            ),
        },
    ]
    response = client.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=EvaluationResult,
    )
    parsed = response.choices[0].message.parsed
    if isinstance(parsed, EvaluationResult):
        return parsed
    if isinstance(parsed, dict):
        return EvaluationResult(**parsed)
    raise SystemExit("OpenAI returned unexpected evaluation format")


def collect_rows(building_id: str, source: str, result: EvaluationResult) -> List[CsvRow]:
    rows: List[CsvRow] = []
    for comparison in result.comparisons:
        rows.append(
            CsvRow(
                source=source,
                building_id=building_id,
                field=comparison.field,
                truth=comparison.truth,
                extracted=comparison.extracted,
                score=comparison.score,
                similar=comparison.similar,
                comment=comparison.comment,
            )
        )
    return rows


def write_csv(rows: List[CsvRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "source",
            "building_id",
            "field",
            "truth",
            "extracted",
            "score",
            "similar",
            "comment",
        ])
        for row in rows:
            writer.writerow(
                [
                    row.source,
                    row.building_id,
                    row.field,
                    row.truth or "",
                    row.extracted or "",
                    row.score if row.score is not None else "",
                    row.similar if row.similar is not None else "",
                    row.comment or "",
                ]
            )


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare extracted Werk fields to the Excel truth data.")
    ap.add_argument("--excel", default="data/251118 Textbeschreibung Werk-material/5_Matrix_Konstruktionstypologie WERK Objekte gui.xlsx", help="Path to the ground-truth Excel file")
    ap.add_argument("--extracted-dir", default="output/task4_openai", help="Folder containing extraction JSONs")
    ap.add_argument("--output", default="output/task4_openai/comparison.csv", help="CSV output path")
    ap.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-5-nano"), help="OpenAI model for scoring")
    ap.add_argument("--dry-run", action="store_true", help="Skip OpenAI calls and use heuristic scoring")
    args = ap.parse_args()

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    truth_map = read_truth(BASE_DIR / args.excel)
    extracted_dir = BASE_DIR / args.extracted_dir
    all_rows: List[CsvRow] = []

    for building_id, truth in truth_map.items():
        for label, suffix in SOURCES:
            extracted = load_extraction(extracted_dir, building_id, suffix)
            if not extracted:
                print(f"[skip] {building_id}{suffix}: no extraction file")
                continue

            if args.dry_run or not api_key:
                result = create_heuristic_result(building_id, truth, extracted)
            else:
                try:
                    result = evaluate_with_openai(api_key, args.model, truth, extracted)
                except Exception as exc:  # pragma: no cover - network calls
                    print(f"[warning] OpenAI evaluation failed for {building_id}{suffix}: {exc}")
                    result = create_heuristic_result(building_id, truth, extracted)

            rows = collect_rows(building_id, label, result)
            all_rows.extend(rows)

    if not all_rows:
        print("No comparison rows produced")
        return

    output_path = BASE_DIR / args.output
    write_csv(all_rows, output_path)
    print(f"Wrote comparison CSV with {len(all_rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
