# Data-audit FC 27

Datum: 2026-10-16 · Dataset: `data/teams-fc27.json`, 622 clubs, geen landenteams

## Aanleiding

Sporting klopte niet en Oekraïne zat in de set. Oorzaak: de FC 27-set was sinds 18 september een kopie van de FC 26-tabel met drie correcties. De dagelijkse build faalde vanaf 20 september op een nieuwe league (`ARKEMA PL`) en nam daarbij ook de FC 26-build mee, dus de echte FC 27-sterren kwamen nooit binnen. Landenteams kwamen voor beide titels uit één seed.

## Wat er nu staat

Sterren komen van fifagamenews FC 27 (bijgewerkt 2026-09-20). Een in-game steekproef bevestigde die waarden, ook waar ze afwijken van EA's pre-release lijst (Newcastle en Galatasaray op 5★). Lidmaatschap wordt getoetst aan fifauteams officiële FC 27-teamlijst (bijgewerkt 2026-10-01, "final"): een club die daar niet op staat valt uit de set.

De schaal is verschoven: FC 27 loopt van 2,0 tot 5,0, er zijn geen clubs meer onder 2 sterren. Van de clubs die in beide sets voorkomen gingen er ruim 350 omhoog en 8 omlaag.

| Sterren | Clubs |
| --- | --- |
| 5.0 | 28 |
| 4.5 | 43 |
| 4.0 | 72 |
| 3.5 | 154 |
| 3.0 | 210 |
| 2.5 | 101 |
| 2.0 | 14 |

## Uit de set: op de bron, niet in de game

- US Saint-Malo (3.0★), `fra.us-saint-malo-w`
- Wieczysta Kraków (3.0★), `pol.wieczysta-krakow`
- Toulouse FC (3.0★), `fra.toulouse-fc-w`
- Zagłębie Lubin (3.0★), `pol.zag-ebie-lubin`
- RC Lens (3.0★), `fra.rc-lens-w`

Klopt een van deze niet, koppel hem dan in `pipeline/aliases.json` onder `teamlijst`.

## In de game, maar zonder ster (niet lootbaar)

De bron heeft voor deze 110 clubs geen ster. Zonder ster kan de app ze niet eerlijk loten, dus ze zitten niet in de set.

- **Zonder licentie (mannen)** (35): AEK Athens, Al Ain FC, APOEL FC, Atlético Nacional, Bahia, Buriram United, Dinamo Kiev, Dinamo Zagreb, Ferencvárosi TC, Hajduk Split, Ludogorets, HJK Helsinki, Olympiacos FC, Omonia Nicosia, Panathinaikos, PAOK, Qarabağ FK, Shakhtar Donetsk, Slavia Praha, Sparta Praha, Viktoria Plzeň, MLS All-Star, Classic League, Bundesliga XI, Chelsea XI, Classic XI, FC Bayern XI, Juventus XI, Liverpool XI, Real Madrid XI, LaLiga XI, Ligue 1 XI, Premier League XI, Serie A XI, Soccer Aid
- **Liga MX** (18): America, Atlas, Atlante, Atlético San Luis, Cruz Azul, Guadalajara, FC Juárez, León, Monterrey, Necaxa, Pachuca, Puebla, Querétaro, Santos Laguna, Tijuana, Toluca, UANL, UNAM
- **Frauen-Bundesliga** (14): 1. FC Köln (W), 1. FC Nürnberg (W), 1899 Hoffenheim (W), Bayer Leverkusen (W), Bayern Munich (W), Eintracht Frankfurt (W), Hamburger SV (W), SC Freiburg (W), Mainz 05 (W), RB Leipzig (W), Stuttgart (W), Union Berlin (W), VfL Wolfsburg (W), Werder Bremen (W)
- **Indian Super League** (14): ATK Mohun Bagan, Bengaluru, Chennaiyin, Diamond Harbour, East Bengal, Goa, SC Delhi, Jamshedpur, Kerala Blasters, Mumbai City, NorthEast United, Odisha, RoundGlass Punjab, United Tigers
- **Zonder licentie (vrouwen)** (13): AFC Richmond (W), Ajax (W), BK Häcken (W), Brann (W), Breidablik (W), FC Zurich (W), Glasgow City (W), Juventus (W), Roma (W), Rosengård (W), Slavia Praha (W), SL Benfica (W), Twente (W)
- **EFL League One** (4): Bromley, Cambridge United, Milton Keynes Dons, Notts County
- **Arkema Première Ligue** (3): Dijon (W), Stade de Reims (W), Thonon Evian (W)
- **Women's Super League** (2): Everton (W), West Ham (W)
- **Ekstraklasa** (2): Arka Gdynia, Polonia Warszawa
- **Liga Profesional** (1): Newell’s
- **Serie A** (1): Udinese
- **Serie B** (1): Vicenza
- **Saudi Pro League** (1): Al Khaleej
- **Swiss Super League** (1): Grasshopper

Wil je er een paar in hebben, zoek ze in-game op en geef de ster door; dan komen ze er handmatig bij.

## Landenteams

Niet in de FC 27-set. Geen enkele bereikbare bron publiceert sterren voor FC 27-landenteams (fifagamenews heeft alleen clubs, EA en fcratings tonen spelerratings, fifaindex en cmtracker blokkeren). De set moet kloppen met wat online staat, dus schatten doen we niet. De filter "Landen" geeft bij FC 27 een lege pool. Komt er een bron, dan krijgt FC 27 een eigen seed via `nationalTeams` in `pipeline/games.json`.

Ter info, de officiële FC 27-lijst (fifauteam, 2026-10-01) noemt 51 mannen- en 18 vrouwenteams, Oekraïne inbegrepen.

## Geborgd

De dagelijkse build bouwt elke titel los: faalt FC 27, dan wordt FC 26 nog steeds gecommit (en andersom), en de job meldt de fout. De build logt bij elke run wat er op de teamlijst staat zonder ster en wat er wegvalt (`TEAMLIJST`).
