# hidle

Enkel pipeline for å hente ut tekst fra høringssvar (HTML/PDF) og lage CSV-filer for videre analyse.

## Datastruktur

- Rådata legges under `data/`
- Ekstraherte tekstfiler skrives til `høringer/`, fordelt på:
  - `høringer/foer-2022/`
  - `høringer/fra-2022/`
  - `høringer/uten-aar/`
- Aggregater som versjoneres i git:
  - `index.csv` (én rad per høringsfil)
  - `aggregering.csv` (oppsummering per år + avsender)

Repoet er satt opp slik at hele arbeidsgrunnlaget kan deles i git, mens tunge binærfiler håndteres med `git-lfs`.

## Kjøring

- Full kjøring (genererer `høringer/`, `index.csv`, `aggregering.csv`):
  - `uv run python main.py`
- Kun rebuild av CSV fra eksisterende `høringer/`:
  - `uv run python main.py --index-only`

Ved eksport prøver pipeline-en først vanlig tekstuttrekk fra PDF. Hvis PDF-en ikke har tekstlag,
brukes OCR som fallback når `pdftoppm` og `tesseract` er tilgjengelige lokalt.

Filer med manglende eller usikkert år havner i `høringer/uten-aar/`.

## Enkel søkeapp (konkordans)

Søkeappen leser `.txt`-filene rekursivt fra alle undermappene i `høringer/` og viser treff med kontekst.

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
Den leser dokumenter rekursivt fra alle tre korpusmappene og behandler dem som ett samlet korpus.

- Start PWA-server:
  - `uv run python pwa_server.py --port 8787`
- Åpne i nettleser:
  - `http://127.0.0.1:8787`
- Funksjoner:
  - korpusvelger for `foer-2022`, `fra-2022`, `uten-aar` eller alle
  - dokumentliste med filter
  - visning av metadata + full tekst
  - konkordanssøk i dokumentinnhold (med kontekst)
  - installbar PWA (manifest + service worker)
  - leser live fra filer i `høringer/foer-2022/`, `høringer/fra-2022/` og `høringer/uten-aar/`

For å åpne to vinduer side om side med hvert sitt korpus, bruk URL-parametere som:

- `http://127.0.0.1:8787/?corpus=foer-2022`
- `http://127.0.0.1:8787/?corpus=fra-2022`

Ved deploy til GitHub Pages bygger workflowen en statisk fil `webapp/data/documents.json`
via `build_static_data.py`. Frontend prøver denne statiske datafilen først, og fallbacker
til lokal `/api` når du kjører `pwa_server.py`.
`webapp/data/documents.json` er versjonert slik at Pages også kan vise dokumentinnhold uten lokal server.

## Git og LFS

Følgende materiale er ment å være versjonert i repoet:

- kode, dokumentasjon og analysefiler
- `høringer/` som delt arbeidskorpus for appen
- `data/` som felles rågrunnlag

Tunge binærfiler legges i `git-lfs`:

- `data/warc/*.warc.gz`
- `data/content/*.pdf`

Lettere tekstfiler som `.html`, `.tsv` og corpus-tekstfiler ligger i vanlig git.

## Git-policy for data

`.gitignore` er satt opp slik at disse mappene ikke versjoneres:

- `data/`
- `høringer/`

Dermed kan vi beholde små, delbare analysefiler i git, mens rådata håndteres lokalt.
