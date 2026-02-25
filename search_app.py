from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

OUTPUT_DIR = Path("høringer")
METADATA_KEYS = ("kilde_fil", "kilde_type", "avsender", "uid", "kilde_uri")


@dataclass
class HearingDocument:
    path: Path
    year: str
    sender: str
    body: str


def parse_hearing_file(path: Path) -> HearingDocument:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    metadata: dict[str, str] = {}
    body_start = 0

    for idx, line in enumerate(lines):
        if ": " in line:
            key, value = line.split(": ", 1)
            if key in METADATA_KEYS:
                metadata[key] = value.strip()
                body_start = idx + 1
                continue
        break

    body = "\n".join(lines[body_start:]).strip()
    sender = metadata.get("avsender", "") or "Ukjent avsender"
    year = path.stem.split("_", 1)[0] if "_" in path.stem else "ukjent"

    return HearingDocument(path=path, year=year, sender=sender, body=body)


def load_documents() -> list[HearingDocument]:
    if not OUTPUT_DIR.exists():
        return []
    return [parse_hearing_file(path) for path in sorted(OUTPUT_DIR.glob("*.txt"))]


def get_matches(pattern: re.Pattern[str], text: str, width: int) -> list[str]:
    snippets: list[str] = []
    for match in pattern.finditer(text):
        start = max(0, match.start() - width)
        end = min(len(text), match.end() + width)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        snippet = (
            f"{prefix}{text[start:match.start()]}"
            f"<b>{match.group(0)}</b>"
            f"{text[match.end():end]}{suffix}"
        )
        snippets.append(" ".join(snippet.split()))
    return snippets


def run_search(
    documents: list[HearingDocument],
    query: str,
    years: set[str],
    senders: set[str],
    context_chars: int,
    max_hits: int,
) -> str:
    pattern = re.compile(re.escape(query.strip()), flags=re.IGNORECASE)
    filtered_docs = [doc for doc in documents if doc.year in years and doc.sender in senders]

    docs_with_hits = 0
    total_hits = 0
    lines: list[str] = []

    for doc in filtered_docs:
        snippets = get_matches(pattern, doc.body, context_chars)
        if not snippets:
            continue

        docs_with_hits += 1
        total_hits += len(snippets)
        lines.append("")
        lines.append(f"=== {doc.path.name} ({len(snippets)} treff) ===")
        lines.append(f"Aar: {doc.year} | Avsender: {doc.sender}")
        for snippet in snippets[:max_hits]:
            lines.append(f"- {snippet}")
        if len(snippets) > max_hits:
            lines.append(f"  ... viser {max_hits} av {len(snippets)} treff")

    lines.append("")
    lines.append(
        f"Treff for '{query}' i {docs_with_hits} dokument(er), totalt {total_hits} forekomster."
    )
    lines.append("")
    return "\n".join(lines)


def parse_csv_filter(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {item.strip() for item in value.split(",") if item.strip()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Enkel konkordans/sok i horinger/")
    parser.add_argument("--query", help="Soketekst. Uten denne starter interaktiv modus.")
    parser.add_argument("--year", help="Filtrer pa ar, kommaseparert, f.eks. 2019,2023")
    parser.add_argument("--sender", help="Filtrer pa avsender, kommaseparert")
    parser.add_argument("--context", type=int, default=90, help="Kontekst i tegn rundt hvert treff")
    parser.add_argument("--max-hits", type=int, default=5, help="Maks treff per dokument")
    parser.add_argument(
        "--output",
        help="Skriv resultat til fil, f.eks. konkordans.txt",
    )
    args = parser.parse_args()

    documents = load_documents()
    if not documents:
        raise SystemExit("Fant ingen tekstfiler i høringer/. Kjør data-pipelinen først.")

    all_years = {doc.year for doc in documents}
    all_senders = {doc.sender for doc in documents}

    year_filter = parse_csv_filter(args.year) or all_years
    sender_filter = parse_csv_filter(args.sender) or all_senders

    if args.query:
        report = run_search(documents, args.query, year_filter, sender_filter, args.context, args.max_hits)
        print(report, end="")
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
            print(f"Skrev konkordans til {output_path.as_posix()}")
        return

    print("Konkordans/sok i høringer/. Skriv tom tekst for a avslutte.")
    while True:
        query = input("Sok> ").strip()
        if not query:
            print("Avslutter.")
            break
        report = run_search(documents, query, year_filter, sender_filter, args.context, args.max_hits)
        print(report, end="")
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
            print(f"Skrev konkordans til {output_path.as_posix()}")


if __name__ == "__main__":
    main()
