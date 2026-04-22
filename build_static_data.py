from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
HEARINGS_DIR = ROOT_DIR / "høringer"
OUTPUT_PATH = ROOT_DIR / "webapp" / "data" / "documents.json"
WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)
METADATA_KEYS = {"kilde_fil", "kilde_type", "avsender", "uid", "kilde_uri"}


def parse_hearing_file(path: Path) -> dict[str, str | int]:
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
    year = path.stem.split("_", 1)[0] if "_" in path.stem else "ukjent"
    sender = metadata.get("avsender", "").strip() or "Ukjent avsender"
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    return {
        "name": path.name,
        "year": year,
        "sender": sender,
        "wordCount": len(WORD_RE.findall(body)),
        "charCount": len(body),
        "modifiedUtc": modified,
        "content": body,
    }


def main() -> None:
    documents: list[dict[str, str | int]] = []
    if HEARINGS_DIR.exists():
        for path in sorted(HEARINGS_DIR.glob("*.txt")):
            documents.append(parse_hearing_file(path))

    if not documents and OUTPUT_PATH.exists():
        existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        existing_count = len(existing.get("documents", []))
        print(
            f"Fant ingen filer i høringer/. Beholder eksisterende {OUTPUT_PATH.as_posix()} "
            f"med {existing_count} dokumenter."
        )
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generatedAtUtc": datetime.now(timezone.utc).isoformat(), "documents": documents}
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"Skrev {OUTPUT_PATH.as_posix()} med {len(documents)} dokumenter")


if __name__ == "__main__":
    main()
