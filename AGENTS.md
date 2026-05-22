# AGENTS.md

## Project Overview

This repo contains a small pipeline and reader app for Norwegian hearing responses.

- Raw/source material lives under `data/`.
- Extracted plain-text hearing files are written to `høringer/`.
- The web app reads from `høringer/` directly through the local server, or from the generated static export in `webapp/data/documents.json`.

## Important Data Paths

- `data/`: source material and intermediate inputs
- `data/content/`: raw HTML/PDF inputs consumed by the export pipeline
- `data/warc/`: WARC exports from Browsertrix
- `høringer/`: extracted `.txt` files used by the app and CLI search
- `høringer/foer-2022/`: extracted files with numeric year before 2022
- `høringer/fra-2022/`: extracted files with numeric year 2022 or later
- `høringer/uten-aar/`: extracted files without a reliable year bucket
- `webapp/data/documents.json`: static frontend data for GitHub Pages / offline use

The app does not read from `data/` directly.

## Current Data Flow

1. `main.py` reads from `data/content/`
2. `main.py` writes extracted text files to one of the three subdirectories inside `høringer/`
3. `pwa_server.py` and `search_app.py` read recursively from all subdirectories in `høringer/`
4. `build_static_data.py` builds `webapp/data/documents.json` from all exported `.txt` files under `høringer/`

If files are moved only inside `data/`, the app will not see that change until `høringer/` is rebuilt.

## Metadata Assumptions

- Year is currently derived from the filename prefix, typically `<year>_...`
- Files without usable metadata may end up with `ukjent` year and `no-uid`
- Some local material may come from WARC-derived sources and therefore lack stable year metadata

Do not assume that every file can be safely assigned to a year bucket just because it exists in `data/`.

## Corpus Split Guidance

The current repo layout uses these review buckets directly under `høringer/`:

- `høringer/foer-2022/`
- `høringer/fra-2022/`
- `høringer/uten-aar/`

Files without a trustworthy numeric year should stay in `høringer/uten-aar/` until manually reviewed.

## If You Change Folder Layout

Any change to the current `høringer/` layout will require coordinated updates in:

- `main.py`
- `search_app.py`
- `pwa_server.py`
- `build_static_data.py`
- `README.md`

The current code already supports recursive reading from the three standard subdirectories above.

## Git Storage Policy

This repo is intended to be shareable as a single workspace for app users and WARC-oriented collaborators.

- Keep `høringer/` versioned in normal git so the app works from the shared corpus.
- Keep text-like source files in `data/` versioned in normal git where practical, including `.html` and `.tsv`.
- Store large binary source files in `git-lfs`, especially:
  - `data/warc/*.warc.gz`
  - `data/content/*.pdf`
- Do not rely on local-only copies of `data/` or `høringer/` when describing the expected project state.
