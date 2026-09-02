# Backlog

Eén kopje per story, met de status *cursief* onder het kopje: *open*,
*(gebouwd, versie)* of *(vervallen, reden)*. Elke story heeft dezelfde vijf
onderdelen: Waarom, Scope / niet in scope, Acceptatiecriteria (afvinkbaar),
Afhankelijkheden en Test. Een nummer is geclaimd zodra het hier op `main`
staat; het volgende vrije nummer staat onderaan. Gebouwde stories blijven
staan, zodat een lezer ziet waarom iets is zoals het is.

## TK-01 Databuild herstellen en bewaken

*(gebouwd, 0.03.3)*

**Waarom.** De snapshot-workflow schreef bij een 522 van fifagamenews een leeg
`stars.html` weg en committe dat. Daardoor faalden twee tests en de offline
build, zonder dat iemand het merkte: de workflow was groen.

**Scope / niet in scope.** In scope: `stars.html` terugzetten uit de laatste
geslaagde fetch, de workflow zo dat alleen een geslaagde en niet-lege fetch een
snapshot overschrijft, en een GitHub-issue bij een mislukking. Niet in scope:
een derde bron (sofifa geeft een Cloudflare-403 aan runners).

**Acceptatiecriteria.**
- [x] `pipeline/snapshots/stars.html` is 601.542 bytes en parseert; `pytest` is groen.
- [x] De offline build levert 654 clubs en 51 landenteams, gelijk aan `data/teams.json`.
- [x] Een fetch die geen 200 met inhoud geeft laat de oude snapshot staan en de workflow faalt.
- [x] Bij een mislukking staat er een issue "Snapshot mislukt" met de run-URL; een tweede open issue met die titel komt er niet.

**Afhankelijkheden.** `permissions: issues: write` in de workflow.

**Test.** `python -m pytest pipeline/tests -q` en
`python pipeline/build_teams.py --offline --skip-colors --skip-crest-check --out /tmp/t.json`.

## TK-02 Escapen van alles wat in innerHTML gaat

*(gebouwd, 0.03.3)*

**Waarom.** Teamnamen uit `teams.json`, duo-namen en scores uit localStorage en
de sync-blob gingen ongefilterd in template-strings. Een kwaadwillende rij op
de bronpagina of een gemanipuleerde stand kon zo script in de pagina zetten.

**Scope / niet in scope.** In scope: één `esc()`-helper op elke interpolatie
van data, het clublogo als element in plaats van HTML-string met inline
handlers, en een parse-guard die een teamnaam met `<` of `>` erin laat falen.
Niet in scope: een template-bibliotheek.

**Acceptatiecriteria.**
- [x] Geen `innerHTML`-toewijzing in `app.js` interpoleert nog ongeëscapete data.
- [x] Geen inline `onload`/`onerror` meer; het logo krijgt zijn handlers via `addEventListener`.
- [x] `parse_stars` en `parse_best_teams` weigeren een naam met `<` of `>` erin; een los teken aan de rand gaat eraf ("> St Mirren").

**Afhankelijkheden.** Geen.

**Test.** `test_parser_rejects_html_in_team_name`; handmatig: een duo-naam
`<b>x</b>` invoeren en zien dat hij letterlijk op de kaart staat.

## TK-03 Sleutel op sync.php

*(gebouwd, 0.03.3)*

**Waarom.** Het endpoint was open: iedereen die de URL raadde kon de stand
lezen en overschrijven, met elke inhoud.

**Scope / niet in scope.** In scope: een gedeelde sleutel in `?key=`,
vergeleken met `hash_equals`; 503 zolang de sleutel niet is ingevuld;
validatie van de PUT-body; CORS alleen voor `https://evenmatch.prulwerk.nl`.
Niet in scope: accounts, per-speler-rechten, een database.

**Acceptatiecriteria.**
- [x] Zonder ingevulde `SLEUTEL` antwoordt het script 503 met een Nederlandse melding.
- [x] Een verkeerde of ontbrekende sleutel geeft 403.
- [x] Een PUT zonder `matches`-lijst, met meer dan 200 matches, met niet-numerieke `sa`/`sb`/`ts` of met een naam langer dan 80 tekens of met `<`/`>` geeft 400.
- [x] `docs/eigen-hosting.md` beschrijft de sleutelstap en de URL-vorm met `?key=`.

**Afhankelijkheden.** Wie al synct moet de sleutel invullen en de URL in de
app aanpassen.

**Test.** `php -l hosting/sync.php`; handmatig met `curl -X PUT` een geldige
en een ongeldige body sturen.

## TK-04 Fonts zelf hosten, script extern, Content-Security-Policy

*(gebouwd, 0.03.3)*

**Waarom.** Google Fonts stond als derde partij in het kritieke pad en maakte
een strikte CSP onmogelijk; het hele script stond inline.

**Scope / niet in scope.** In scope: Archivo 400 en 900 in `fonts/`, het
script naar `app.js`, en een CSP die alleen eigen scripts en fonts toelaat.
Niet in scope: de variabele Archivo met breedte-as (zie TK-18).

**Acceptatiecriteria.**
- [x] Geen verwijzing naar `fonts.googleapis.com` of `fonts.gstatic.com` meer.
- [x] `index.html` bevat geen inline `<script>` en geen `javascript:`-URL.
- [x] De CSP-meta staat in de head; de app werkt er volledig onder (logo's, flagcdn, raw.githubusercontent, sync).

**Afhankelijkheden.** Geen.

**Test.** Pagina laden met de console open: nul CSP-meldingen.

## TK-05 Service worker

*(gebouwd, 0.03.3)*

**Waarom.** De README beloofde "alles offline" maar dat gold alleen voor de
iOS-app; de webapp had geen enkele offline-voorziening.

**Scope / niet in scope.** In scope: netwerk eerst, cache als terugval voor
eigen bestanden, precache van pagina, script, manifest, iconen en fonts,
cachenaam met versie, oude caches weg bij activeren. Niet in scope: de
dataset in de cache (zie TK-13), push, background sync.

**Acceptatiecriteria.**
- [x] Na één bezoek opent de site in vliegtuigmodus.
- [x] Een nieuwe `APP_VERSION` maakt een nieuwe cache en ruimt de oude op.
- [x] `manifest.json` heeft `id`, `scope`, `lang` en `purpose: "any maskable"` op de iconen.

**Afhankelijkheden.** TK-04 (het script moet extern zijn om het te precachen).

**Test.** DevTools > Application > Service Workers; offline aanvinken en
herladen.

## TK-06 Workflow-hygiëne

*(gebouwd, 0.03.3)*

**Waarom.** `data.yml` draaide op elke branch die `pipeline/` raakte, dus een
`claude/*`-branch kon een live scrape en een commit veroorzaken. De tests
zaten in de dagelijkse scrape in plaats van in CI, dependencies stonden op
`>=`, en de workflows hadden geen expliciete rechten.

**Scope / niet in scope.** In scope: `data.yml` alleen op `main`, checkout van
`main` bij de dagelijkse run, pytest naar `ci.yml`, issue bij een mislukte
build, exacte versies in `requirements.txt`, `permissions` in elke workflow.
Niet in scope: Dependabot.

**Acceptatiecriteria.**
- [x] Een push naar een niet-`main` branch start `data.yml` niet.
- [x] `ci.yml` draait pytest naast de Swift-tests bij elke wijziging in `pipeline/`.
- [x] Bij een mislukte databuild staat er een issue "Databuild mislukt" met run-URL.
- [x] `requirements.txt` bevat alleen `==`.

**Afhankelijkheden.** Geen.

**Test.** `python -c "import yaml; ..."` op elke workflow; een run van CI na de merge.

## TK-07 bundled-teams.json verversen

*(gebouwd, 0.03.3)*

**Waarom.** De ingebakken iOS-set liep achter op `data/teams.json`, dus een
toestel zonder netwerk startte met oude sterren.

**Scope / niet in scope.** In scope: een kopie van `data/teams.json`. Niet in
scope: automatisch verversen in CI (die zou dan elke dag een app-commit maken).

**Acceptatiecriteria.**
- [x] `app/Teamkiezeer/Resources/bundled-teams.json` is byte-gelijk aan `data/teams.json` op het moment van de release.

**Afhankelijkheden.** Geen.

**Test.** `cmp data/teams.json app/Teamkiezeer/Resources/bundled-teams.json`.

## TK-08 FC 27-overgang

*open*

**Waarom.** In september verschijnt FC 27. De bron-URL's, het `game`-veld, de
snapshots en de ankerwaarden in `audit.py` zijn allemaal op FC 26 gepind.

**Scope / niet in scope.** In scope: `STARS_URL` en `BEST_TEAMS_URL` in
`build_teams.py`, `game` in de output, de drie URL's in `snapshot.yml`, verse
snapshots, de ankers en de `leagues.json`-titels nalopen. Niet in scope: twee
games naast elkaar ondersteunen.

**Acceptatiecriteria.**
- [ ] De build leest de FC 27-pagina's en `teams.json` zegt `"game": "FC 27"`.
- [ ] De snapshots zijn van de FC 27-pagina's en `pytest` is groen.
- [ ] Elke ankerwaarde in `audit.py` is tegen de nieuwe lijst gecontroleerd.
- [ ] De kopregel in de webapp en de app tonen "EA FC 27".

**Afhankelijkheden.** De bronsites moeten de FC 27-pagina's live hebben.

**Test.** Volledige build plus de audit; een handmatige spot-check van tien
teams in-game.

## TK-09 Cron terug naar 0 7 bij wintertijd

*open*

**Waarom.** Cron is UTC. `0 6 * * *` is 08:00 in de zomer en 07:00 in de
winter; het commentaar in `data.yml` zegt het al.

**Scope / niet in scope.** In scope: eind oktober de regel op `0 7 * * *`
zetten, eind maart terug. Niet in scope: een tweede workflow die zomertijd
uitrekent.

**Acceptatiecriteria.**
- [ ] Tussen eind oktober en eind maart staat er `0 7 * * *`.

**Afhankelijkheden.** Geen.

**Test.** De run-tijd in Actions is 08:00 Europe/Amsterdam.

## TK-10 Drop-entries in leagues.json weg zodra fifauteam fixt

*open*

**Waarom.** Op de bronpagina tonen "Österreichische Bundesliga" en "Women's
Super League" een kopie van respectievelijk de A-League en de NWSL. Beide
worden gedropt; hun clubs zijn daardoor `league: null` en nooit lootbaar.

**Scope / niet in scope.** In scope: de twee `drop`-regels verwijderen zodra
`test_known_duplicate_leagues_are_copies` faalt (dat is het signaal dat de
bron gefixt is). Niet in scope: de teams handmatig aanvullen.

**Acceptatiecriteria.**
- [ ] `test_known_duplicate_leagues_are_copies` is verwijderd of omgekeerd.
- [ ] Beide leagues staan in `teams.json` met minstens 8 teams.

**Afhankelijkheden.** fifauteam.

**Test.** `pytest` en de audit (leagues met <8 teams breken de build).

## TK-11 Landenteam-sterren in-game controleren

*open*

**Waarom.** De sterren en ratings van de 51 landenteams in
`data/national-teams.json` zijn schattingen; er is geen scrapebare bron.

**Scope / niet in scope.** In scope: elk landenteam in-game opzoeken en de
seed corrigeren. Niet in scope: een nieuwe bron scrapen.

**Acceptatiecriteria.**
- [ ] Elk landenteam heeft een in-game gecontroleerde ster en rating, met de datum van de check in het bestand.

**Afhankelijkheden.** Iemand met de game.

**Test.** De audit blijft groen (bereik 0,5 tot 5 en 40 tot 99).

## TK-12 aliases.json vullen

*open*

**Waarom.** 29 clubs staan als `unk.*` in `teams.json`: hun naam op de
sterrenpagina matcht niet met de ratings-pagina, dus ze hebben geen league en
zijn nooit lootbaar. `aliases.json` is leeg.

**Scope / niet in scope.** In scope: per `UNMATCHED`-regel in de buildlog
bepalen of het een naamverschil is en dan een alias toevoegen. Niet in scope:
de Franse vrouwenclubs zonder league op de ratings-pagina (die zijn bewust
uitgesloten, zie data-audit.md).

**Acceptatiecriteria.**
- [ ] Elke `unk.*`-club is óf gealiast óf met een reden genoemd in data-audit.md.

**Afhankelijkheden.** Geen.

**Test.** De build logt geen `UNMATCHED` meer voor gealiaste namen; het aantal
clubs met league stijgt.

## TK-13 Ingebedde DATA-literal verkleinen of vervangen

*open*

**Waarom.** `app.js` draagt een dataset van 158 KB van 21 augustus als
offline-terugval. Die is oud, zonder crests, en wordt bij elk bezoek geladen
terwijl de service worker (TK-05) nu een betere plek is.

**Scope / niet in scope.** In scope: `data/teams.json` in de precache zetten
en de literal terugbrengen tot wat de eerste render nodig heeft, of helemaal
weg. Niet in scope: een ander dataformaat.

**Acceptatiecriteria.**
- [ ] `app.js` is kleiner dan 60 KB.
- [ ] Offline (na één bezoek) toont de app de laatst geladen dataset, niet die van 21 augustus.
- [ ] De kopregel knippert niet (zie 0.03.0).

**Afhankelijkheden.** TK-05.

**Test.** Vliegtuigmodus na één bezoek; de datadatum in de kopregel is die van
het laatste bezoek.

## TK-14 dominant_colors cachen

*open*

**Waarom.** De dagelijkse build haalt ~650 crests op om per team een
fallback-kleur te bepalen, terwijl die kleur alleen verandert als het
logo verandert.

**Scope / niet in scope.** In scope: een cache per `crestURL` (bestand in de
repo of in de Actions-cache) of de kleurstap wekelijks draaien. Niet in
scope: de crests zelf committen (EA/club-IP).

**Acceptatiecriteria.**
- [ ] Een dagelijkse build met ongewijzigde crest-URL's doet geen crest-requests.
- [ ] Een nieuwe of gewijzigde URL krijgt wél een verse kleur.

**Afhankelijkheden.** Geen.

**Test.** De buildlog telt de crest-requests.

## TK-15 Eerlijke User-Agent en alleen het tabelfragment in snapshots

*open*

**Waarom.** De scraper doet zich voor als Chrome op een Mac en de snapshots
zijn complete pagina's van 0,6 tot 1 MB, inclusief scripts en advertenties die
de parser nooit leest.

**Scope / niet in scope.** In scope: een User-Agent die zegt wat het is
(`EvenMatch-build/x (+https://evenmatch.prulwerk.nl)`), en in `snapshot.yml`
alleen het `<table>`-deel bewaren. Niet in scope: een andere bron.

**Acceptatiecriteria.**
- [ ] De bron accepteert de eerlijke User-Agent (anders: documenteren en terug).
- [ ] Snapshots bevatten alleen de tabellen en de tab-titels die `parse.py` leest; `pytest` blijft groen.

**Afhankelijkheden.** De bronsites.

**Test.** `pytest` tegen de nieuwe snapshots.

## TK-16 Contrast meten als test

*open*

**Waarom.** Het palet in `index.html` is op het oog gecontroleerd. De
Asteria-site heeft laten zien dat "op het oog" in donker vijf botsingen
overslaat.

**Scope / niet in scope.** In scope: een script dat de kleurtokens uit
`index.html` leest en het contrast van tekst op elk vlak toetst (AA), als
test. Niet in scope: een herontwerp van het palet.

**Acceptatiecriteria.**
- [ ] Een test faalt zodra een tekstkleur onder 4,5:1 zakt op het vlak waarop hij staat.

**Afhankelijkheden.** Geen.

**Test.** De test zelf.

## TK-17 Stale branches verwijderen

*open, eigenaar*

**Waarom.** Werk dat op een branch blijft staan wordt twee keer gedaan. Op de
remote staan nu `claude/menu-pulldown-refresh-bug-ej6n2w`,
`claude/menu-pulldown-refresh-bug-vn208s`, `claude/national-team-crests-t8itzj`,
`claude/new-project-welcome-npwul9`, `claude/team-selectie-audit-cjl44d` (gemerged
in 0.03.3) en `gh-pages` (Pages serveert de root van `main`).

**Scope / niet in scope.** In scope: per branch nakijken of er iets
ongemerged op staat, en dan verwijderen. Niet in scope: een branch-protectie
instellen.

**Acceptatiecriteria.**
- [ ] `git branch -r` toont alleen `main` (en de branch van de sessie die op dat moment werkt).

**Afhankelijkheden.** Alleen de eigenaar kan remote branches verwijderen.

**Test.** `git branch -r`.

## TK-18 Archivo met breedte-as zelf hosten

*open*

**Waarom.** De pagina zet `font-stretch:125%` op de scoreboard-cijfers en de
koppen. De zelfgehoste instances uit TK-04 zijn statisch op normale breedte
(widthClass 5, geen `fvar`), dus die stretch doet nu niets en de cijfers zijn
smaller dan bedoeld.

**Scope / niet in scope.** In scope: een Archivo-instance op wdth 125 (of de
variabele font met alleen de gebruikte assen) toevoegen aan `fonts/` en de
`@font-face`-regels met `font-stretch` uitbreiden. Niet in scope: een ander
lettertype.

**Acceptatiecriteria.**
- [ ] De scoreboard-cijfers renderen op wdth 125 zonder externe host.
- [ ] De extra bestanden samen blijven onder 60 KB.

**Afhankelijkheden.** TK-04.

**Test.** Visuele vergelijking met een schermafdruk van vóór 0.03.3.

---

**Volgend vrij nummer: TK-19**
