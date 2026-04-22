# hidle

Enkel pipeline for å hente ut tekst fra høringssvar (HTML/PDF) og lage CSV-filer for videre analyse.

## Datastruktur

- Rådata legges under `data/` (ignoreres av git)
- Ekstraherte tekstfiler skrives til `høringer/` (ignoreres av git)
- Aggregater som versjoneres i git:
  - `index.csv` (én rad per høringsfil)
  - `aggregering.csv` (oppsummering per år + avsender)

Dette gjør repoet lett å dele uten å sjekke inn store råfiler.

## Kjøring

- Full kjøring (genererer `høringer/`, `index.csv`, `aggregering.csv`):
  - `uv run python main.py`
- Kun rebuild av CSV fra eksisterende `høringer/`:
  - `uv run python main.py --index-only`

## Enkel søkeapp (konkordans)

Søkeappen leser `.txt`-filene direkte fra `høringer/` og viser treff med kontekst.

- Start interaktiv modus:
  - `uv run python search_app.py`
- Kjør direkte med søk + filter:
  - `uv run python search_app.py --query grunnrente --year 2019 --max-hits 3`
- Skriv konkordanse til fil:
  - `uv run python search_app.py --query grunnrente --year 2019 --output konkordans.txt`
- Tilgjengelige filtre/parametre:
  - `--year` (kommaseparert)
  - `--sender` (kommaseparert)
  - `--context` (tegn rundt treff)
  - `--max-hits` (maks treff per dokument)
  - `--output` (filsti for resultat)

## PWA for høringer/

En enkel PWA lar deg bla i og lese dokumenter direkte fra `høringer/` via en lokal server.

- Start PWA-server:
  - `uv run python pwa_server.py --port 8787`
- Åpne i nettleser:
  - `http://127.0.0.1:8787`
- Funksjoner:
  - dokumentliste med filter
  - visning av metadata + full tekst
  - installbar PWA (manifest + service worker)
  - leser live fra filer i `høringer/`

## Git-policy for data

`.gitignore` er satt opp slik at disse mappene ikke versjoneres:

- `data/`
- `høringer/`

Dermed kan vi beholde små, delbare analysefiler i git, mens rådata håndteres lokalt.
