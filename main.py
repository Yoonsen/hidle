from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from html import unescape
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

DATA_DIR = Path("data")
CONTENT_DIR = DATA_DIR / "content"
OUTPUT_DIR = Path("høringer")
BEFORE_2022_DIR = OUTPUT_DIR / "foer-2022"
FROM_2022_DIR = OUTPUT_DIR / "fra-2022"
WITHOUT_YEAR_DIR = OUTPUT_DIR / "uten-aar"
INDEX_PATH = Path("index.csv")
AGGREGATION_PATH = Path("aggregering.csv")

UID_RE = re.compile(r"uid=([a-f0-9-]{36})", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)

logging.getLogger("pypdf").setLevel(logging.ERROR)


@dataclass
class HearingMeta:
    sender: str
    source_uri: str
    year_group: str


def normalize_ws(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = SPACE_RE.sub(" ", text)
    return text.strip()


def clean_block_text(text: str) -> str:
    text = unescape(text).replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    lines: list[str] = []
    for line in text.split("\n"):
        line = normalize_ws(line)
        if line:
            lines.append(line)
    return "\n".join(lines)


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "ukjent-avsender"


def load_metadata() -> dict[str, HearingMeta]:
    uid_to_meta: dict[str, HearingMeta] = {}
    tsv_paths = [
        (DATA_DIR / "2019-type_uri_avsender.tsv", "2019"),
        (DATA_DIR / "2023-type_uri_avsender.tsv", "2023"),
    ]

    for tsv_path, year_group in tsv_paths:
        if not tsv_path.exists():
            continue

        with tsv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                uri = (row.get("uri") or "").strip()
                sender = (row.get("avsender") or "").strip()
                uid_match = UID_RE.search(uri)
                if not uid_match:
                    continue
                uid = uid_match.group(1)
                uid_to_meta[uid] = HearingMeta(
                    sender=sender or "Ukjent avsender",
                    source_uri=uri,
                    year_group=year_group,
                )

    return uid_to_meta


def exported_text_paths() -> list[Path]:
    if not OUTPUT_DIR.exists():
        return []
    return sorted(path for path in OUTPUT_DIR.rglob("*.txt") if path.is_file())


def infer_year_from_stem(path: Path) -> str:
    if "_" in path.stem:
        return path.stem.split("_", 1)[0]
    return "ukjent"


def corpus_dir_for_year(year_value: str) -> Path:
    if year_value.isdigit():
        return BEFORE_2022_DIR if int(year_value) < 2022 else FROM_2022_DIR
    return WITHOUT_YEAR_DIR


def extract_uid(raw_html: str) -> str | None:
    match = UID_RE.search(raw_html)
    if not match:
        return None
    return match.group(1)


def extract_html_text(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")

    # Skip overview/listing pages; we only want individual hearing responses.
    if soup.select_one(".hearing-search") is not None:
        return ""

    # Most individual hearing response pages have this structure.
    hearing_answer = soup.select_one(".hearing-answer")
    if hearing_answer is None:
        return ""

    parts: list[str] = []
    header = soup.select_one(".article-header h1")
    ingress = hearing_answer.select_one(".article-ingress")
    timestamp = hearing_answer.select_one(".hearing-answer-timestamp")
    body = hearing_answer.select_one(".article-body")
    for section in (header, ingress, timestamp, body):
        if section:
            section_text = clean_block_text(section.get_text("\n", strip=True))
            if section_text:
                parts.append(section_text)
    return "\n\n".join(parts)


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        page_text = normalize_ws(page_text)
        if page_text:
            pages.append(page_text)
    return "\n\n".join(pages)


def write_output(
    source_path: Path,
    text: str,
    uid: str | None,
    meta: HearingMeta | None,
) -> Path:
    sender = meta.sender if meta else "Ukjent avsender"
    year_group = meta.year_group if meta else "ukjent"
    target_dir = corpus_dir_for_year(year_group)
    uid_value = uid or "no-uid"
    if uid_value == "no-uid":
        source_id = hashlib.sha1(source_path.name.encode("utf-8")).hexdigest()[:10]
        filename = f"{year_group}_{slugify(sender)}_{uid_value}_{source_id}.txt"
    else:
        filename = f"{year_group}_{slugify(sender)}_{uid_value}.txt"
    out_path = target_dir / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    header_lines = [
        f"kilde_fil: {source_path.as_posix()}",
        f"kilde_type: {source_path.suffix.lower().lstrip('.')}",
        f"avsender: {sender}",
        f"uid: {uid_value}",
        f"kilde_uri: {meta.source_uri if meta else ''}",
        "",
    ]

    out_path.write_text("\n".join(header_lines) + text.strip() + "\n", encoding="utf-8")
    return out_path


def parse_exported_text_file(path: Path) -> dict[str, str | int]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    metadata: dict[str, str] = {}
    body_start = 0
    expected_keys = {"kilde_fil", "kilde_type", "avsender", "uid", "kilde_uri"}

    for idx, line in enumerate(lines):
        if ": " in line:
            key, value = line.split(": ", 1)
            if key in expected_keys:
                metadata[key] = value.strip()
                body_start = idx + 1
                continue
        break

    body_text = "\n".join(lines[body_start:]).strip()
    year_group = infer_year_from_stem(path)

    return {
        "filnavn": path.name,
        "sti": path.as_posix(),
        "aar": year_group,
        "avsender": metadata.get("avsender", ""),
        "uid": metadata.get("uid", ""),
        "kilde_type": metadata.get("kilde_type", ""),
        "kilde_fil": metadata.get("kilde_fil", ""),
        "kilde_uri": metadata.get("kilde_uri", ""),
        "antall_tegn": len(body_text),
        "antall_ord": len(WORD_RE.findall(body_text)),
    }


def build_index() -> int:
    rows: list[dict[str, str | int]] = []
    for txt_path in exported_text_paths():
        rows.append(parse_exported_text_file(txt_path))

    fieldnames = [
        "filnavn",
        "sti",
        "aar",
        "avsender",
        "uid",
        "kilde_type",
        "kilde_fil",
        "kilde_uri",
        "antall_tegn",
        "antall_ord",
    ]
    with INDEX_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def _safe_int(value: str | int) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_aggregation() -> int:
    if not INDEX_PATH.exists():
        raise SystemExit("Fant ikke index.csv. Kjør indeksbygging først.")

    grouped: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"antall_horinger": 0, "sum_antall_ord": 0, "sum_antall_tegn": 0}
    )

    with INDEX_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            aar = (row.get("aar") or "ukjent").strip() or "ukjent"
            avsender = (row.get("avsender") or "Ukjent avsender").strip() or "Ukjent avsender"
            key = (aar, avsender)
            grouped[key]["antall_horinger"] += 1
            grouped[key]["sum_antall_ord"] += _safe_int(row.get("antall_ord", 0))
            grouped[key]["sum_antall_tegn"] += _safe_int(row.get("antall_tegn", 0))

    rows: list[dict[str, str | int | float]] = []
    for (aar, avsender), values in grouped.items():
        antall = values["antall_horinger"]
        sum_ord = values["sum_antall_ord"]
        rows.append(
            {
                "aar": aar,
                "avsender": avsender,
                "antall_horinger": antall,
                "sum_antall_ord": sum_ord,
                "sum_antall_tegn": values["sum_antall_tegn"],
                "snitt_antall_ord": round(sum_ord / antall, 2) if antall else 0,
            }
        )

    rows.sort(
        key=lambda r: (
            str(r["aar"]),
            -_safe_int(r["sum_antall_ord"]),
            str(r["avsender"]).lower(),
        )
    )

    fieldnames = [
        "aar",
        "avsender",
        "antall_horinger",
        "sum_antall_ord",
        "sum_antall_tegn",
        "snitt_antall_ord",
    ]
    with AGGREGATION_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Eksporter høringer og bygg index.csv")
    parser.add_argument(
        "--index-only",
        action="store_true",
        help="Bygg kun index.csv fra eksisterende filer i høringer/",
    )
    args = parser.parse_args()

    if args.index_only:
        if not OUTPUT_DIR.exists():
            raise SystemExit("Fant ikke høringer/. Kjør uten --index-only først.")
        index_count = build_index()
        print(f"Skrev {INDEX_PATH.as_posix()} med {index_count} rader")
        aggregation_count = build_aggregation()
        print(f"Skrev {AGGREGATION_PATH.as_posix()} med {aggregation_count} rader")
        return

    if not CONTENT_DIR.exists():
        raise SystemExit("Fant ikke data/content. Sjekk at dataene er kopiert inn.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for existing_txt in exported_text_paths():
        existing_txt.unlink()

    uid_to_meta = load_metadata()

    written: list[Path] = []
    written_set: set[Path] = set()
    overwritten = 0
    skipped = 0

    for path in sorted(CONTENT_DIR.iterdir()):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        try:
            if suffix == ".html":
                raw_html = path.read_text(encoding="utf-8", errors="ignore")
                uid = extract_uid(raw_html)
                meta = uid_to_meta.get(uid) if uid else None
                text = extract_html_text(raw_html)
                if not text:
                    skipped += 1
                    continue
                out = write_output(path, text, uid, meta)
                if out in written_set:
                    overwritten += 1
                else:
                    written_set.add(out)
                    written.append(out)
            elif suffix == ".pdf":
                text = extract_pdf_text(path)
                if not text:
                    skipped += 1
                    continue
                out = write_output(path, text, None, None)
                if out in written_set:
                    overwritten += 1
                else:
                    written_set.add(out)
                    written.append(out)
            else:
                skipped += 1
        except Exception as exc:  # noqa: BLE001
            print(f"ADVARSEL: klarte ikke lese {path.name}: {exc}")
            skipped += 1

    print(f"Skrev {len(written)} tekstfiler til {OUTPUT_DIR.as_posix()}/")
    print(f"Overskrev {overwritten} duplikater (samme avsender/uid)")
    print(f"Hoppet over {skipped} filer")
    index_count = build_index()
    print(f"Skrev {INDEX_PATH.as_posix()} med {index_count} rader")
    aggregation_count = build_aggregation()
    print(f"Skrev {AGGREGATION_PATH.as_posix()} med {aggregation_count} rader")


if __name__ == "__main__":
    main()
