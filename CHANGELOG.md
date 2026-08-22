# Changelog

Versienummers volgen `0.MM.P`: `MM` gaat omhoog bij nieuwe features, `P` bij
fixes. De webapp toont zijn versie onderin de Filters-sheet; de iOS-app
volgt hetzelfde nummer via `MARKETING_VERSION` in het Xcode-project.
Releasen = versie bumpen op beide plekken + regel hieronder + push naar main.

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
