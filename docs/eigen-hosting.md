# Even Match op je eigen site (FTP)

De app is puur statisch, dus draaien op je eigen hosting = bestanden
uploaden. Bonus: heeft je hosting PHP (vrijwel altijd), dan wordt je site
ook meteen de **gedeelde score-opslag** voor alle spelers.

## Uploaden

Zet via FTP in een map (bijv. `/evenmatch/`):

- `index.html`
- `manifest.json`
- `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`
- `hosting/sync.php` → upload als `sync.php`

Teamdata hoef je **niet** te uploaden: de app haalt die zelf rechtstreeks
van GitHub (de weekly scrape) en valt alleen terug op een lokale kopie als
GitHub onbereikbaar is. Wil je die fallback ook: upload `data/teams.json`
als `teams.json` ernaast en ververs die af en toe.

## Gedeelde scores aanzetten

1. Open de app op je site → sectie **Stand** → veld **Sync-URL**.
2. Vul in: `https://jouwdomein.nl/evenmatch/sync.php`
3. Doe dit op elk apparaat dat mee moet doen (eenmalig).

Vanaf dan haalt elk apparaat bij het openen de laatste stand op en pusht
elke opgeslagen score naar je site. `evenmatch-stand.json` verschijnt
vanzelf naast het script — dat bestand is de hele "database", dus een
back-up is een kwestie van downloaden.

Let op: het endpoint is bewust simpel en open (geen login). Voor een
huiskamer-app prima; zet er geen gevoelige data in en gebruik desnoods een
onraadbare mapnaam.

## Bijwerken

Nieuwe app-versie: alleen `index.html` opnieuw uploaden. De teamdata en de
stand werken onafhankelijk daarvan.
