# Data-audit: kloppen de sterren?

Datum: 2026-08-21 · Dataset: FC 26, 654 clubs + 51 landenteams

## Wat is gecontroleerd

**1. Kruisconsistentie tussen twee onafhankelijke bronnen.** Er bestaat geen
tweede publieke sterrenlijst om 1-op-1 tegen te leggen (fifagamenews is dé
lijst; fifauteam publiceert voor FC 26 geen sterren per team). Daarom toetst
de audit de sterren (fifagamenews) tegen de squad ratings (fifauteam), die
van een andere site komen: per sterrenbucket moet de gemiddelde squad rating
strikt oplopen, en geen enkel team mag ver van zijn bucketgemiddelde liggen.

Resultaat: **alle 10 buckets strikt monotoon, nul uitschieters** (>6 OVR van
het bucketgemiddelde). De twee bronnen bevestigen elkaar; een verwisselde
kolom, kapotte join of verschoven rij zou hier direct zichtbaar zijn.

| Sterren | Teams | Gem. OVR |
| --- | --- | --- |
| 5.0 | 13 | ~84 |
| 4.5 | 24 | ~81 |
| 4.0 | 78 | ~78 |
| 3.5 | 97 | ~75 |
| 3.0 | 110 | ~72 |
| 2.5–0.5 | 332 | aflopend |

**2. Ankerteams.** Bekende waarden worden elke build gecontroleerd
(`pipeline/audit.py`): PSG/Real/Barcelona/Arsenal/Liverpool/Bayern op 5★
(harde ondergrens 4★), Ajax 4★, PSV 4★. Drift wordt gelogd als waarschuwing
(seizoensupdate), een breuk onder de ondergrens breekt de build (parsefout).

**3. Actualiteit.** De bron werkt sterren bij gedurende het seizoen; onze
Action scrapet elke maandag en commit alleen bij wijzigingen. `generatedAt`
staat in de app (Regels-scherm) en op de website in de kop. De snapshot van
vandaag is identiek aan de live pagina's (fetch-log 200's, zelfde bytes).

**4. Landenteams gevalideerd tegen de officiële FC 26-lijst.** De
handmatige seed is vergeleken met fifauteams "FC 26 Leagues, Clubs & National
Teams". Gevolg: **België, Japan, Colombia, Uruguay, Zwitserland en Turkije
zijn verwijderd — die zitten niet in FC 26.** Toegevoegd: Ghana, Tsjechië,
Hongarije, Roemenië, Oekraïne, Wales, Ierland, Noord-Ierland, Canada, China,
Qatar, Finland, IJsland, Nieuw-Zeeland, plus 13 vrouwenlandenteams. Sterren
en ratings van landenteams blijven schattingen (geen scrapebare bron) —
in-game spot-check blijft de bedoeling, het bestand is daarvoor ingericht.

## Bekende, bewuste beperkingen

- **Landenteams hebben geen crest-bron.** fifauteam/fifagamenews tonen
  landenteams als platte tekst zonder logo per team (anders dan clubs, die
  wel een crest-URL per rij hebben). `pipeline/build_teams.py` vult
  `crestURL` voor landenteams daarom in met een vlag via
  `pipeline/flags.json` (countryCode -> flagcdn.com-landcode) i.p.v. een
  officieel bondslogo; de audit faalt hard als een landenteam zonder
  crestURL blijft.
- **Franse vrouwenclubs** (OL Lyonnes, PSG (v), Fleury, Dijon, "Nantes",
  "Le Havre", …) staan op de sterrenlijst zonder (W)-markering en hun league
  (Première Ligue) staat niet op de ratings-pagina. Ze krijgen `league: null`,
  vallen buiten elke whitelist en zijn dus nooit lootbaar — liever eerlijk
  uitgesloten dan gegokt.
- **Kopie-leagues op de bron** (Oostenrijkse Bundesliga = A-League, WSL =
  NWSL) worden gedropt; hun clubs zijn daardoor ook league-null. Een assertie
  breekt de build zodra de bron nieuwe identieke teamlijsten toont — of deze
  juist fixt (dan faalt de fixture-test en kan de drop weg).
- **Duplicaten op de sterrenlijst** (PSG, Marseille, Lens, Strasbourg,
  Montpellier, Saint-Étienne, Paris FC) zijn de vrouwenteams zonder marker;
  dedup houdt de eerste (mannen-)rij en logt elke gedropte rij.

## Hoe dit wekelijks geborgd blijft

`python pipeline/build_teams.py` draait `run_audit()` op elke build (dus ook
in de weekly Action). Hard falen: clubaantal buiten 550–800, <85% league-match,
niet-monotone buckets, ratings buiten 40–99, leagues met <8 teams, ankers
onder hun ondergrens. Waarschuwen: ankerdrift en bucket-uitschieters.
Een build die hard faalt commit níéts — de app en site blijven dan op de
laatste goede dataset staan.
