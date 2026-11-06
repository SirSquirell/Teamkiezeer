# Data-audit FC 27

Datum: 2026-11-06 · Dataset: `data/teams-fc27.json`, 754 clubs in 43 competities plus Rest of World, 51 landenteams (mannen)

## Aanleiding

Sporting klopte niet. Onderzoek liet zien dat de oude FC 27-set op drogzand stond: fifagamenews' "FC 27"-sterren zijn een formule (vaste banden op team-OVR, 5★ vanaf 81) op fifauteams teamratings van seizoen 2025/26. De pagina bevat zelfs een verborgen regel "we'll keep this page updated with FC 26 values", mist Liga MX en de Frauen-Bundesliga, en zet Dortmund, United, Chelsea, Roma, Napoli en Spurs op 5★ waar EA zelf 4,5★ publiceerde.

## Bronnen nu

**Clubs en competities: EA zelf.** EA's FC 27-ratingsite (ea.com/games/ea-sports-fc/ratings) bevat per competitie de clubs, met mannen/vrouwen per groep: 754 clubs, 63 groepen. De dagelijkse build leest die pagina; de koppeling naar onze league-ids staat in `pipeline/ea-leagues-fc27.json`. Groepjes van een paar clubs (Olympiacos, Shakhtar, Slavia, …) zijn EA's Rest of World en staan onder "Rest of World". Een nieuwe EA-competitie laat de build bewust falen.

**Sterren: `pipeline/stars-fc27.json`, per club met zijn basis.** Een complete online lijst met echte FC 27-sterren bestaat niet (de sites die de gamedatabase lezen, zoals fifaindex, sofifa, cmtracker en futbin, blokkeren automatische toegang). Daarom per club de hardste beschikbare bron, in deze volgorde:

| Basis | Clubs | Wat |
| --- | --- | --- |
| `ea-officieel` | 32 | EA's eigen sterrenlijst (top 16 mannen en 16 vrouwen) |
| `in-game` | 23 | uit de game afgelezen (Vandal, 365Scores Liga MX, allthings.how) |
| `ovr-gemeten` | 266 | echte FC 27-team-OVR uit de gamedatabase (cmtracker, fctoolshub, fifaindex, sofifa via zoekresultaten), omgezet met EA's grenzen |
| `model` | 433 | team-OVR berekend uit EA's officiële FC 27-spelersratings (beste elftal, lijngemiddelden), zelfde grenzen |

Sterrengrenzen op team-OVR: 83 = 5★, 80 = 4,5★, 75 = 4★, 72 = 3,5★, 68 = 3★, 64 = 2,5★, 60 = 2★. De bovenste twee zijn vastgepind door EA's lijst naast gemeten OVR (Liverpool 83 = 5★, Dortmund en Spurs 81 = 4,5★) en een in-game check: Newcastle 79 = 4★. EA zette Aston Villa (nu 79) in augustus nog op 4,5★; die lijst is van voor de release, dus bij mannenclubs wint de huidige gemeten OVR.

## Hoe goed is het model

Twee agents bouwden onafhankelijk een model (een op de bekende teamrating-methode, een puur op de data). Op de 201 clubs met gemeten OVR uit ronde 1 zat het gecombineerde model gemiddeld 0,5 OVR naast de echte waarde en gaf het in 83% exact dezelfde ster. Ronde 2 mat 93 clubs die juist dicht bij een stergrens lagen: daar klopte het model bij 80 (86%). Elke misser is een halve ster. Clubs met basis `model` zijn dus meestal goed maar niet gegarandeerd. Elke in-game check die afwijkt hoort in `pipeline/overrides-fc27.json`.

## Wat afwijkt van eerdere meldingen

- Sporting CP: 4★ (gemeten OVR 77), niet 4,5★.
- Newcastle: 4★ (in-game gecheckt, OVR 79). Daarmee gingen alle clubs op 79 van 4,5★ naar 4★, onder meer Galatasaray, Fenerbahçe, Leverkusen, Leipzig, Porto, Villa en Forest.
- Atlético Madrid: EA's lijst zegt 5★ (OVR 83), Vandal 4,5★; de set volgt EA.
- Liga MX: 365Scores (in-game) en cmtracker verschillen 1–2 OVR; de set volgt de in-game sterren.

## Landenteams

`data/national-teams-fc27.json`: de 51 mannenteams van de officiële FC 27-lijst (fifauteam fc-27-leagues-clubs-national-teams, gecheckt 2026-11-06), geen team dat alleen in FC 26 zat (China m/v, Canada m). Team-OVR/ATT/MID/DEF komen uit de FC 27-gamedatabase (sofifa, db-update 2026-11-03; Nederland 82/80/84/82 klopt ook bij cmtracker), dus basis `ovr-gemeten`, harder dan de 433 clubs op `model`. Sterren via dezelfde grenzen als de clubs.

Open punten:

- Of EA voor landenteams dezelfde sterrengrenzen hanteert als voor clubs is niet bewezen. Met de clubgrenzen staan zes landen op 5★ (Frankrijk, Spanje, Engeland, Portugal, Duitsland, Brazilië) en vijf op 4,5★ (Italië, Nederland, Argentinië, België, Kroatië). Een ongesourcede lijst (gamermovil, okt 2026) zet alle tien op 5★. In-game check nodig; afwijkingen in `pipeline/overrides-fc27.json`.
- Oekraïne staat op de officiële lijst én in de database, maar een in-game check van 2026-10-16 zag het team niet. Staat erin tot dat opnieuw gecheckt is.
- De 18 vrouwenteams ontbreken nog: pas toevoegen met gemeten OVR, niet geschat.

## Uitbreiden

Meer clubs van `model` naar `ovr-gemeten` brengen: per club de FC 27-OVR opzoeken (zoekterm "<club> FC 27 career mode overall rating cmtracker" werkt het best) en in `stars-fc27.json` zetten met `basis: ovr-gemeten` en de bron.
