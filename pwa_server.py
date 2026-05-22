from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "webapp"
HEARINGS_DIR = ROOT_DIR / "høringer"
WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)
METADATA_KEYS = {"kilde_fil", "kilde_type", "avsender", "uid", "kilde_uri"}


def exported_text_paths() -> list[Path]:
    if not HEARINGS_DIR.exists():
        return []
    return sorted(path for path in HEARINGS_DIR.rglob("*.txt") if path.is_file())


def document_id_for_path(path: Path) -> str:
    return path.relative_to(HEARINGS_DIR).as_posix()


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

    stat = path.stat()
    modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

    return {
        "id": document_id_for_path(path),
        "name": path.name,
        "corpus": path.parent.name,
        "year": year,
        "sender": sender,
        "wordCount": len(WORD_RE.findall(body)),
        "charCount": len(body),
        "modifiedUtc": modified,
        "content": body,
    }


def safe_document_path(document_id: str) -> Path | None:
    candidate = (HEARINGS_DIR / document_id).resolve()
    try:
        candidate.relative_to(HEARINGS_DIR.resolve())
    except ValueError:
        return None
    if not candidate.is_file() or candidate.suffix.lower() != ".txt":
        if "/" in document_id or "\\" in document_id:
            return None
        matches = [path for path in exported_text_paths() if path.name == document_id]
        return matches[0] if len(matches) == 1 else None
    return candidate


class PwaHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "documentsDir": HEARINGS_DIR.as_posix()})
            return

        if parsed.path == "/api/documents":
            if not HEARINGS_DIR.exists():
                self.send_json(
                    {"documents": [], "warning": "Fant ikke høringer/"},
                    status=HTTPStatus.OK,
                )
                return

            docs: list[dict[str, str | int]] = []
            for path in exported_text_paths():
                parsed_file = parse_hearing_file(path)
                docs.append(
                    {
                        "id": str(parsed_file["id"]),
                        "name": str(parsed_file["name"]),
                        "corpus": str(parsed_file["corpus"]),
                        "year": str(parsed_file["year"]),
                        "sender": str(parsed_file["sender"]),
                        "wordCount": int(parsed_file["wordCount"]),
                        "charCount": int(parsed_file["charCount"]),
                        "modifiedUtc": str(parsed_file["modifiedUtc"]),
                    }
                )
            self.send_json({"documents": docs})
            return

        if parsed.path == "/api/document":
            query = parse_qs(parsed.query)
            raw_document_id = query.get("id", [""])[0]
            raw_name = query.get("name", [""])[0]
            document_id = unquote(raw_document_id)
            name = unquote(raw_name)
            lookup_value = document_id or name
            if not lookup_value:
                self.send_json({"error": "Mangler query-param: id"}, status=HTTPStatus.BAD_REQUEST)
                return

            path = safe_document_path(lookup_value)
            if path is None:
                self.send_json({"error": "Dokument ikke funnet"}, status=HTTPStatus.NOT_FOUND)
                return

            data = parse_hearing_file(path)
            self.send_json(data)
            return

        if parsed.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Kjor lokal PWA for høringer/")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8787, help="Port (default: 8787)")
    args = parser.parse_args()

    if not WEB_DIR.exists():
        raise SystemExit("Fant ikke webapp/.")

    server = ThreadingHTTPServer((args.host, args.port), PwaHandler)
    print(f"PWA server kjorer pa http://{args.host}:{args.port}")
    print("Trykk Ctrl+C for a stoppe.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
