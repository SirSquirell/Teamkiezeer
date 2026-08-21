# Even Match

*Two teams. Dead even.*

2v2 team picker voor EA FC Kick-Off (repo-naam: Teamkiezeer; de app en site heten **Even Match**). Eén knop: **Draw**. De app kiest twee teams
met identieke sterren, dezelfde soort (club vs. landenteam), en een squad-rating
verschil binnen de afgesproken marge — met een korte slot-machine ceremony.

Puur voor eigen gebruik, nooit voor de App Store.

**Direct gebruiken (niets installeren):** https://sirsquirell.github.io/Teamkiezeer/

## Layout

```
/pipeline      Python scraper, draait wekelijks in GitHub Actions
index.html     de webapp — GitHub Pages serveert de repo-root van main
/app           Xcode project (SwiftUI, iOS 17+)
/data          gegenereerde teams.json + handmatige national-teams.json
```

## Data

- Sterren: fifagamenews.com FC 26 team star ratings
- Squad rating + league: fifauteam.com best teams
- Landenteams: handmatig in `data/national-teams.json`
- Crests: runtime gefetcht via URL, nooit gecommit (EA/club-IP)

De GitHub Action draait de scraper wekelijks en commit `data/teams.json` alleen
bij een non-empty diff. De app haalt dat bestand bij launch op via
raw.githubusercontent, met cache- en bundled-fallback zodat alles offline werkt.

## Bouwen (app)

1. Open `app/Teamkiezeer.xcodeproj` in Xcode 16+.
2. Zet je eigen team onder Signing & Capabilities (personal team is genoeg).
3. Run op een iPhone met iOS 17+.

De engine-tests draaien ook zonder Mac: `swift test` in `app/TeamkiezeerKit`
(gebeurt automatisch in CI op elke push).

Op je iPhone zetten (gratis Apple ID, TestFlight of sideload via de
CI-gebouwde IPA): zie [docs/op-je-telefoon.md](docs/op-je-telefoon.md).

### Mac-app (dmg)

Elke app-wijziging bouwt CI ook een Mac-versie (Mac Catalyst):
Actions → **Build IPA** → laatste run → artifact **EvenMatch-dmg**.
De app is niet gesigneerd, dus de eerste keer openen gaat via
rechtermuisklik op "Even Match.app" → **Open** → nogmaals *Open*
(of System Settings → Privacy & Security → *Open Anyway*).

Vernieuw af en toe de ingebouwde offline-snapshot:

```
cp data/teams.json app/Teamkiezeer/Resources/bundled-teams.json
```

## Onderhoud

- Eigen hosting via FTP (incl. gedeelde scores): zie docs/eigen-hosting.md.
- Nieuwe league op de bronpagina? De build faalt bewust; voeg de league toe
  aan `pipeline/leagues.json`.
- Naam-mismatch tussen de twee bronpagina's? Vul `pipeline/aliases.json`
  (de build logt elke unmatched naam).
- Landenteams: handmatig bijwerken in `data/national-teams.json`.
- FC 27 in september: pas de twee bron-URL's aan in `pipeline/build_teams.py`
  en het `game`-veld; ververs daarna de snapshots voor de tests.
