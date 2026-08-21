# Teamkiezeer

2v2 team picker voor EA FC Kick-Off. Eén knop: **Draw**. De app kiest twee teams
met identieke sterren, dezelfde soort (club vs. landenteam), en een squad-rating
verschil binnen de afgesproken marge — met een korte slot-machine ceremony.

Puur voor eigen gebruik, nooit voor de App Store.

## Layout

```
/pipeline      Python scraper, draait wekelijks in GitHub Actions
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
