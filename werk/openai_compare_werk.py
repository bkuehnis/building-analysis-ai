#!/usr/bin/env python3
"""
Tasks 4-6: Use OpenAI to extract structured fields from Werk-material building data.

Reads:
    data/werk/{id}/datasheet.json   (preferred)
    data/werk/{id}/datasheet.html   (fallback)
    data/werk/{id}/images/*         (for Task 5)

Writes:
    output/task4_openai/{id}_text.json
    output/task4_openai/{id}_images.json
    output/task4_openai/{id}_comparison.json
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field


class WerkExtraction(BaseModel):
    jahr_fertigstellung: Optional[str] = Field(None, alias="Jahr (Fertigstellung)")
    Ort: Optional[str] = Field(None, alias="Ort")
    Architekt: Optional[str] = Field(None, alias="Architekt")
    Dach: Optional[str] = Field(None, alias="Dach")
    Aussenwand: Optional[str] = Field(None, alias="Aussenwand")
    Fenster: Optional[str] = Field(None, alias="Fenster")
    Tragwerk: Optional[str] = Field(None, alias="Tragwerk")
    Decke: Optional[str] = Field(None, alias="Decke")
    Innenwaende: Optional[str] = Field(None, alias="Innenwände")
    Haustechnik: Optional[str] = Field(None, alias="Haustechnik")


DEFAULT_BUILDING_IDS = ["57403"]
MAX_IMAGE_COUNT = 20


def encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def list_images(building_dir: Path) -> List[Path]:
    if not building_dir.exists() or not building_dir.is_dir():
        return []
    exts = {".jpg", ".jpeg", ".png", ".gif", ".tiff", ".tif", ".bmp", ".webp"}
    return [p for p in sorted(building_dir.iterdir()) if p.suffix.lower() in exts and p.is_file()]


def build_content(
    mode: str,
    context_text: Optional[str],
    image_paths: List[Path],
    max_images: int = 3,
) -> List[Dict[str, Any]]:
    question = (
        "Bitte extrahiere folgende Informationen: Jahr (Fertigstellung), Ort, Architekt, Dach, "
        "Aussenwand, Fenster, Tragwerk, Decke, Innenwände, Haustechnik. Wenn etwas nicht ersichtlich ist, "
        "setze null."
    )

    content: List[Dict[str, Any]] = [{"type": "text", "text": question}]

    if mode in {"combined", "text"} and context_text:
        content.append({"type": "text", "text": f"KONTEXT:\n{context_text}"})

    if mode in {"combined", "images"} and image_paths:
        for path in image_paths[:max_images]:
            mime, _ = mimetypes.guess_type(str(path))
            if not mime:
                mime = "image/jpeg"
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{encode_image(path)}"}
                }
            )

    return content


def call_openai(api_key: str, model: str, content: List[Dict[str, Any]]) -> Dict[str, Any]:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Du extrahierst strukturierte Baudaten aus einem gegebenen Datenblatt-Text oder Bildern.\n"
                    "Regeln:\n"
                    "- Nutze nur Informationen aus dem bereitgestellten Kontext.\n"
                    "- Wenn etwas fehlt/unklar ist: null.\n"
                    '- "Jahr (Fertigstellung)" bitte als 4-stellige Jahreszahl (z.B. "1996") falls möglich; '
                    "wenn nur ein Datum vorhanden ist, extrahiere das Jahr; sonst null.\n"
                    '- "Architekt" aus Feld "Architektur" (Namen/Firma), ohne Zusatzrollen.\n'
                    "- Dach/Aussenwand/Fenster/Tragwerk/Decke/Innenwände aus dem Abschnitt 'Konstruktion' "
                    "oder ähnlichen Beschreibungen.\n"
                    "- Haustechnik aus 'Gebäudetechnik' oder ähnlichen Beschreibungen.\n"
                ),
            },
            {"role": "user", "content": content},
        ],
        response_format=WerkExtraction,
    )
    parsed = response.choices[0].message.parsed
    if isinstance(parsed, WerkExtraction):
        return parsed.model_dump()
    if isinstance(parsed, dict):
        return parsed
    return {}


def query_openai(
    api_key: str,
    model: str,
    mode: str,
    context_text: Optional[str],
    image_paths: List[Path],
    max_images: int = MAX_IMAGE_COUNT,
) -> Dict[str, Any]:
    content = build_content(mode, context_text, image_paths, max_images)
    return call_openai(api_key=api_key, model=model, content=content)


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


def _safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_datasheet_json(building_dir: Path) -> Optional[Dict[str, Any]]:
    p = building_dir / "datasheet.json"
    if not p.exists():
        return None
    try:
        return json.loads(_safe_read_text(p))
    except Exception:
        return None


def parse_datasheet_html(building_dir: Path) -> Optional[Dict[str, str]]:
    p = building_dir / "datasheet.html"
    if not p.exists():
        return None

    html = _safe_read_text(p)
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return None

    data: Dict[str, str] = {}
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) >= 2:
            key = tds[0].get_text(" ", strip=True)
            val = tds[1].get_text(" ", strip=True)
            if key:
                data[key] = val
    return data or None


def normalize_context(datasheet: Dict[str, Any]) -> str:
    # Keep the prompt small but informative. Prefer the most relevant long text fields if present.
    preferred_order = [
        "Name",
        "Ort",
        "Gemeinde",
        "Kanton",
        "Land",
        "Strasse",
        "Nr.",
        "Fertigstellung",
        "Architektur",
        "Konstruktion",
        "Gebäudetechnik",
        "Projektinformation",
    ]

    lines: List[str] = []

    # First: preferred keys in order
    for k in preferred_order:
        if k in datasheet and datasheet[k]:
            v = datasheet[k]
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False)
            lines.append(f"{k}: {str(v).strip()}")

    # Then: the rest (short keys/values)
    for k, v in datasheet.items():
        if k in preferred_order:
            continue
        if v is None:
            continue
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        v = str(v).strip()
        if not v:
            continue
        # Avoid repeating huge blobs twice
        if len(v) > 800:
            continue
        lines.append(f"{k}: {v}")

    return "\n".join(lines).strip()


def extract_year(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    match = re.search(r"\b(19|20)\d{2}\b", str(value))
    return match.group(0) if match else None


def find_sentence(text: Optional[str], keyword: str) -> Optional[str]:
    if not text:
        return None
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    for sentence in sentences:
        if keyword.lower() in sentence.lower():
            return sentence.strip()
    return None


def extract_from_sections(datasheet: Dict[str, Any], keyword: str) -> Optional[str]:
    for section in ("Konstruktion", "Gebäudetechnik", "Projektinformation"):
        value = datasheet.get(section)
        sentence = find_sentence(value, keyword)
        if sentence:
            return sentence
    return None


def extract_truth_fields(datasheet: Dict[str, Any]) -> Dict[str, Optional[str]]:
    truth: Dict[str, Optional[str]] = {
        "Jahr (Fertigstellung)": extract_year(datasheet.get("Fertigstellung")),
        "Ort": datasheet.get("Ort"),
        "Architekt": datasheet.get("Architektur"),
    }

    for field in ("Dach", "Aussenwand", "Fenster", "Tragwerk", "Decke", "Innenwände"):
        truth[field] = extract_from_sections(datasheet, field)

    truth["Haustechnik"] = (
        datasheet.get("Gebäudetechnik")
        or extract_from_sections(datasheet, "Haustechnik")
        or extract_from_sections(datasheet, "Haus")
    )

    return truth


def normalize_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(value).strip())
    return cleaned.lower() if cleaned else None


def values_equal(left: Optional[str], right: Optional[str]) -> bool:
    normalized_left = normalize_value(left)
    normalized_right = normalize_value(right)
    if normalized_left is None or normalized_right is None:
        return False
    return normalized_left == normalized_right


def compare_results(
    text_result: Dict[str, Any],
    image_result: Dict[str, Any],
    truth_fields: Dict[str, Optional[str]],
) -> Dict[str, Any]:
    entries = []
    for field in FIELDS:
        text_value = text_result.get(field)
        image_value = image_result.get(field)
        truth_value = truth_fields.get(field)

        entries.append(
            {
                "field": field,
                "text": text_value,
                "image": image_value,
                "truth": truth_value,
                "text_matches_image": values_equal(text_value, image_value),
                "text_matches_truth": values_equal(text_value, truth_value),
                "image_matches_truth": values_equal(image_value, truth_value),
            }
        )

    return {
        "truth": truth_fields,
        "text_result": text_result,
        "image_result": image_result,
        "fields": entries,
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")



def iter_building_ids(
    data_dir: Path,
    ids: Optional[List[str]],
    all_ids: bool,
    fallback: Optional[List[str]] = None,
) -> List[str]:
    if ids:
        return ids
    if all_ids:
        if not data_dir.exists():
            return []
        return sorted([p.name for p in data_dir.iterdir() if p.is_dir()])
    if fallback:
        return fallback
    raise SystemExit("Provide --id ... or --all")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", action="append", help="Building id (repeatable), e.g. --id 58237")
    ap.add_argument("--all", action="store_true", help="Process all ids in data/werk/")
    ap.add_argument("--data-dir", default="data/werk", help="Path to data/werk (default: data/werk)")
    ap.add_argument("--out-dir", default="output/task4_openai", help="Output dir (default: output/task4_openai)")
    ap.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-5-nano"), help="OpenAI model")
    ap.add_argument("--dry-run", action="store_true", help="Do not call OpenAI; just print context length")
    ap.add_argument(
        "--max-images",
        type=int,
        default=MAX_IMAGE_COUNT,
        help="Max number of images to send per request (default: 3)",
    )
    args = ap.parse_args()
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key and not args.dry_run:
        raise SystemExit("Missing OPENAI_API_KEY env var")

    base_dir = Path(__file__).parent.parent
    data_dir = (base_dir / args.data_dir).resolve()
    out_dir = (base_dir / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    building_ids = iter_building_ids(data_dir, args.id, args.all, fallback=DEFAULT_BUILDING_IDS)

    for bid in building_ids:
        bdir = data_dir / bid
        if not bdir.exists():
            print(f"[skip] {bid}: not found at {bdir}")
            continue

        datasheet = load_datasheet_json(bdir)
        if datasheet is None:
            datasheet = parse_datasheet_html(bdir) or {}

        context_text = normalize_context(datasheet)
        if not context_text:
            print(f"[skip] {bid}: empty datasheet context")
        image_paths = list_images(bdir)

        if args.dry_run:
            print(
                f"[dry-run] {bid}: context chars={len(context_text)}, images={len(image_paths)}"
            )
            continue

        text_result: Dict[str, Any] = {}
        image_result: Dict[str, Any] = {}

        if context_text:
            try:
                text_result = query_openai(
                    api_key=api_key,
                    model=args.model,
                    mode="text",
                    context_text=context_text,
                    image_paths=[],
                )
                write_json(out_dir / f"{bid}_text.json", text_result)
            except Exception as exc:  # pragma: no cover - network call
                print(f"[error] {bid} text extraction failed: {exc}")
        else:
            print(f"[skip-text] {bid}: no datasheet context")

        if image_paths:
            try:
                image_result = query_openai(
                    api_key=api_key,
                    model=args.model,
                    mode="images",
                    context_text=None,
                    image_paths=image_paths,
                    max_images=args.max_images,
                )
                write_json(out_dir / f"{bid}_images.json", image_result)
            except Exception as exc:  # pragma: no cover - network call
                print(f"[error] {bid} image extraction failed: {exc}")
        else:
            print(f"[skip-images] {bid}: no images found")
            
        if image_paths and context_text:
            try:
                image_result = query_openai(
                    api_key=api_key,
                    model=args.model,
                    mode="combined",
                    context_text=context_text,
                    image_paths=image_paths,
                    max_images=args.max_images,
                )
                write_json(out_dir / f"{bid}_images_text.json", image_result)
            except Exception as exc:  # pragma: no cover - network call
                print(f"[error] {bid} image extraction failed: {exc}")
        else:
            print(f"[skip-combined] {bid}: no images or text found")



if __name__ == "__main__":
    main()