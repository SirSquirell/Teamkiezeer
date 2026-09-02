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
van GitHub (de dagelijkse scrape) en valt alleen terug op een lokale kopie als
GitHub onbereikbaar is. Wil je die fallback ook: upload `data/teams.json`
als `teams.json` ernaast en ververs die af en toe.

## Gedeelde scores aanzetten

1. Open `sync.php` in een editor en vul bij `const SLEUTEL = '';` een
   eigen sleutel in van minimaal 32 tekens (bijvoorbeeld de uitkomst van
   `openssl rand -hex 24`). Zonder sleutel weigert het script alles met
   een 503, zodat een vergeten stap nooit stil een open endpoint oplevert.
2. Open de app op je site → sectie **Stand** → veld **Sync-URL**.
3. Vul in: `https://jouwdomein.nl/evenmatch/sync.php?key=JOUW-SLEUTEL`
4. Doe dit op elk apparaat dat mee moet doen (eenmalig).

Vanaf dan haalt elk apparaat bij het openen de laatste stand op en pusht
elke opgeslagen score naar je site. `evenmatch-stand.json` verschijnt
vanzelf naast het script — dat bestand is de hele "database", dus een
back-up is een kwestie van downloaden.

De sleutel is het enige slot: wie de URL kent kan de stand lezen en
overschrijven. Deel de URL dus alleen met wie meespeelt, en zet er geen
gevoelige data in. Het script accepteert alleen een stand in het verwachte
formaat (maximaal 200 matches, namen zonder `<` of `>`) en antwoordt alleen
op verzoeken vanaf `https://evenmatch.prulwerk.nl`; host je de app zelf
onder een ander domein, pas dan de `Access-Control-Allow-Origin`-regel in
`sync.php` aan.

## Bijwerken

Nieuwe app-versie: alleen `index.html` opnieuw uploaden. De teamdata en de
stand werken onafhankelijk daarvan.
