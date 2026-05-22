# Arkiverte høringsuttalelser

Dette området inneholder høringsbrev arkivert fra `regjeringen.no`, knyttet til to saker:
- [NOU 2019: 18 "Grunnrenteskatt på havbruk"](https://www.regjeringen.no/no/dokumenter/horing--nou-2019-18-skattlegging-av-havbruk/id2676532/)
- [Prop. 78 LS (2022-23) "Grunnrenteskatt på havbruk"](https://www.regjeringen.no/no/dokumenter/horing-grunnrenteskatt-pa-havbruk/id2929159/)

Dataene er høstet med av nettarkivet med Browsertrix.

## Data og formater

Arkivdataene ligger under `./warc` og er i [WARC-format](https://iipc.github.io/warc-specifications/specifications/warc-format/warc-1.1/), og er enkelt forklart en transkripsjon av dialogen mellom NBs innhøster og serverne på nett. Disse kan brukes til å avspille innholdet i en visningstjeneste, og inkluderer nødvendige css- og javascript-ressurser.

WARC-ressursene er også parset til html og pdf med `warcio`, og ligger under `./content`. Dette er altså et filtrert uttrekk fra WARCfilene av records, der:
-  `WARC-Type` er `response``
- payload har http status kode `200``
- innholdet er gjenkjent som enten `html` eller `pdf`

## Kontekst

For å etablere metadata om avsender per innholdsressurs kan man benytte tab-separerte filer generert under scoping av innhøstingen.
- `2019-type_uri_avsender.tsv`
- `2023-type_uri_avsender.tsv` 

Syv html-filer er inkludert for å gi kontekst og oversikt over de to sakene. Disse bør ikke inngå i datagrunnlaget for tekstanalyse:

### Kontekst 2023:
https://www.regjeringen.no/no/dokumenter/horing-grunnrenteskatt-pa-havbruk/id2929159/?showSvar=true&consterm=&page=1&isFilterOpen=true
https://www.regjeringen.no/no/dokumenter/horing-grunnrenteskatt-pa-havbruk/id2929159/?showSvar=true&consterm=&isFilterOpen=true&page=2
https://www.regjeringen.no/no/dokumenter/horing-grunnrenteskatt-pa-havbruk/id2929159/?showSvar=true&consterm=&isFilterOpen=true&page=3
https://www.regjeringen.no/no/dokumenter/horing-grunnrenteskatt-pa-havbruk/id2929159/?showSvar=true&consterm=&isFilterOpen=true&page=4
https://www.regjeringen.no/no/dokumenter/horing-grunnrenteskatt-pa-havbruk/id2929159/?showSvar=true&consterm=&isFilterOpen=true&page=5

### Kontekst 2019:
https://www.regjeringen.no/no/dokumenter/horing--nou-2019-18-skattlegging-av-havbruk/id2676532/?showSvar=true&consterm=&isFilterOpen=true&page=2
https://www.regjeringen.no/no/dokumenter/horing--nou-2019-18-skattlegging-av-havbruk/id2676532/?expand=horingsresultat&lastvisited=undefined