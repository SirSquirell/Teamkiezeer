# Changelog

Versienummers volgen `0.MM.P`: `MM` gaat omhoog bij nieuwe features, `P` bij
fixes. De webapp toont zijn versie onderin de Filters-sheet; de iOS-app
volgt hetzelfde nummer via `MARKETING_VERSION` in het Xcode-project.
Releasen = versie bumpen op beide plekken + regel hieronder + push naar main.

## 0.03.3 — 2026-08-25

- **De iOS/Mac-engine filterde nog wél op ratingverschil.** In 0.03.0 verdween
  `maxRatingDelta` uit de webapp, maar `TeamkiezeerKit/DrawEngine` trok nog
  altijd uniform over de *paren* binnen delta 2. Gevolg: teams die met hun
  squad rating aan de rand van hun sterbucket zaten kregen minder
  tegenstanders en dus minder kans (spreiding 1,77x), en twee teams konden
  helemaal nooit vallen — Paris FC (4★, rating 72 tussen clubs van 75+) en
  Al Hazem. De versoepelingsladder redde die niet, want zolang de pool ergens
  één geldig paar heeft komt de engine nooit aan trap 1 toe. De engine trekt
  nu, net als de webapp, twee teams uniform binnen de sterbucket: elk trekbaar
  team zit exact op 2/N. Daarmee vervalt de instelling "Max. rating-verschil"
  in het Rules-scherm; de rating blijft op de kaart en in de balansmeter staan.
- **Het herhaalfilter keek in de webapp alleen naar gespeelde matches**, niet
  naar de rolls. Doorrollen filterde dus niets weg, ook niet als je 'm hoger
  zette. Hij telt nu élke recente trekking — rolls, de gekozen eindmatch en
  gespeelde matches — nieuwste eerst, en een paar dat zowel gerold als
  gespeeld is telt één keer.
- **Herhaalfilter versoepelt niet meer alles-of-niets.** Past er met de
  ingestelde diepte geen paar meer (kleine pool, bijvoorbeeld 8 clubs op
  5 sterren), dan krimpt het venster stap voor stap tot er wél een paar past
  in plaats van het filter helemaal te laten vallen. De kaart meldt hoe ver
  hij nog terugkeek: "herhaalfilter beperkt tot 3 draws".
- **"Niet herhalen binnen" standaard op 6** (was 0), gelijk aan de iOS-app.
  De opslagsleutel is `rules6`: bestaande toestellen starten dus eenmalig op
  de nieuwe defaults, wat meteen een league-filter opruimt dat ooit per
  ongeluk dichtstond.
- **Nieuw: `pipeline/draw_audit.py`.** Rekent de exacte trekkingskans per team,
  league en land uit voor een filterstand, meldt structureel onbereikbare
  teams en de spreiding tussen de wel-trekbare teams.

## 0.03.2 — 2026-08-22

- **Databuild draait nu dagelijks (08:00 Europe/Amsterdam) i.p.v. wekelijks.**
  `.github/workflows/data.yml` cron gewijzigd naar `0 6 * * *`; teksten in
  app-footer, README en docs die "wekelijks" noemden zijn meegewerkt naar
  "dagelijks". Cron is UTC en volgt de zomertijd niet automatisch — 06:00 UTC
  komt tijdens CET (winter) op 07:00 lokaal binnen; zie het commentaar bij de
  cron-regel om 'm dan terug te zetten naar `0 7 * * *`.

## 0.03.1 — 2026-08-22

- **Landenteams hadden nooit een crest.** De scrape-bronnen tonen
  landenteams als platte tekst zonder logo per team, dus `crestURL` bleef
  altijd `null` en de kaart viel stil terug op de lege plaatshouder (zichtbaar
  op alle landenteam-matchups). `pipeline/build_teams.py` vult `crestURL`
  nu met een vlag (`pipeline/flags.json` -> flagcdn.com) per landenteam; de
  audit faalt hard als een landenteam alsnog zonder crest blijft.

## 0.03.0 — 2026-08-22

- **Max ratingverschil is weg.** Gelijk aantal sterren is dé
  eerlijkheidsregel; de squad rating staat nog op de kaarten maar filtert
  niet meer. De relaxatieladder is daarmee ook simpeler (alleen het
  herhaalfilter kan nog loslaten).
- **"Niet herhalen binnen" standaard op 0** (was 6).
- Geen flikkerende teller meer bij het laden: de kopregel verschijnt pas
  als de verse dataset binnen is, in plaats van eerst de ingebakken
  offline-set te tonen en daarna om te klappen.
- Kopregel toont nu "EA FC 26", de datadatum als dd-mm en het
  app-versienummer — versie is zo altijd zichtbaar op het hoofdscherm.

## 0.02.0 — 2026-08-22

- Nieuwe standaardinstellingen: Teams op **Mix**, **vaste ster 4**,
  vrouwenteams uit, max ratingverschil 2, cooldown 6, alle leagues aan.
  Bestaande toestellen krijgen deze defaults ook (instellingen-reset).
- League-teller in de Filters-sheet gefixt (telde onzichtbare
  vrouwencompetities mee: "35 van 32 aan").
- Versiebeheer: zichtbaar versienummer in de app + dit changelog.
- Sterren-correcties: `pipeline/overrides.json` — een gemelde foute ster
  (of squad rating) wordt daar vastgelegd en overleeft elke weekly scrape;
  de build meldt het zodra de bron is bijgetrokken. Sterren zijn leidend,
  de squad rating blijft gewoon zichtbaar op de kaarten.

## 0.01.1 — 2026-08-21

- Herontwerp van de webapp (v3): kaart-materiaal per sterrating, rustiger
  draw-ceremony, Filters/Stand als sheets, desktop-rail.
- Eindmatch-flow: GENERATE → KIES → optioneel score invullen (met
  verplicht "'t stoeltje"); ongescoorde matches blijven "niet gespeeld".
- Stand & rapportage als aparte popup; history verwijderbaar (gekoppeld);
  gedeelde stand via optionele Sync-URL (`hosting/sync.php`).
- Live op https://evenmatch.prulwerk.nl (GitHub Pages, main-root).

## 0.01.0 — 2026-08-20

- Eerste werkende versie: Python-scrapepipeline met weekly GitHub Action
  en zelf-audit, seedbare matching-engine (identieke sterren, clubs nooit
  tegen landen, ratingdelta, cooldown), iOS-app (SwiftUI) + ongesigneerde
  IPA en Mac-dmg uit CI, webapp op GitHub Pages.
