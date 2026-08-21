# Teamkiezeer op je iPhone krijgen

De app gaat nooit naar de App Store, dus installeren = zelf signeren. Drie
routes, van simpel naar comfortabel. Voor alle drie geldt eenmalig op de
iPhone: **Instellingen → Privacy & beveiliging → Ontwikkelaarsmodus** aan
(toestel herstart).

## Route 1 — Mac + kabel, gratis Apple ID (start hier)

Kosten: niks. Nadeel: de app verloopt na **7 dagen** en moet dan opnieuw
vanuit Xcode geïnstalleerd worden (gewoon nogmaals op Run drukken).

1. Open `app/Teamkiezeer.xcodeproj` in Xcode 16+.
2. Xcode → Settings → Accounts → voeg je Apple ID toe (gratis account is genoeg).
3. Target *Teamkiezeer* → Signing & Capabilities → Team: je *Personal Team*.
   Xcode past de bundle-id eventueel zelf aan met een suffix; prima.
4. iPhone met kabel aansluiten → "Vertrouw deze computer" → kies je toestel
   als run-destination → **Run**.
5. Eerste keer op de iPhone: Instellingen → Algemeen → VPN en apparaatbeheer
   → jouw Apple ID → *Vertrouw*.

Limieten gratis account: apps verlopen na 7 dagen, max 3 sideloaded apps
tegelijk, max 10 app-id's per week.

## Route 2 — Apple Developer Program (€99/jaar, meeste comfort)

Met een betaald account blijft een geïnstalleerde build **1 jaar** geldig, en
belangrijker: **TestFlight** wordt mogelijk.

- Zelfde stappen als route 1, maar met je betaalde team geselecteerd. Klaar.
- Of via TestFlight: archive in Xcode (Product → Archive) → upload naar App
  Store Connect → interne TestFlight-groep met alleen jezelf. Installeren en
  updaten gaat dan draadloos via de TestFlight-app; builds zijn 90 dagen
  geldig en een nieuwe build pushen is genoeg om te verlengen.
- "Nooit naar de App Store" blijft gelden: interne TestFlight vereist geen
  App Review.

## Route 3 — Zonder Mac in de buurt: CI bouwt de IPA, jij signeert lokaal

De GitHub Action **Build IPA** (`.github/workflows/ipa.yml`) bouwt bij elke
app-wijziging een ongesigneerde `Teamkiezeer-unsigned.ipa` en hangt die als
artifact aan de run (Actions → Build IPA → laatste run → Artifacts).

Die IPA signeer en installeer je met een sideload-tool met je eigen Apple ID:

- **Sideloadly** (Mac/Windows): IPA + iPhone aan de kabel, Apple ID invullen,
  Start. Zelfde 7-dagenregel bij een gratis account.
- **AltStore** (Mac/Windows als "AltServer" op hetzelfde wifi): vernieuwt de
  handtekening **automatisch** elke week zolang je computer af en toe aanstaat
  — de minst irritante gratis optie.
- **SideStore**: fork van AltStore die na eenmalige setup zonder computer kan
  vernieuwen.

## Welke route past?

| | Kosten | Verloopt | Kabel nodig | Gedoe |
| --- | --- | --- | --- | --- |
| 1. Xcode gratis | €0 | 7 dagen | elke week | laag |
| 2. Dev-account / TestFlight | €99/jr | 1 jr / 90 dgn | nee (TestFlight) | eenmalig |
| 3. CI-IPA + AltStore | €0 | 7 dgn, auto-verniewd | alleen eerste keer | eenmalige setup |

Praktisch advies: begin met route 1 om te zien of alles bevalt. Wordt de
wekelijkse herinstallatie irritant, kies dan route 3 (AltStore) of gooi er
€99 tegenaan voor TestFlight.

## Updates & data

Nieuwe teamdata heeft **geen** herinstallatie nodig: de app haalt
`data/teams.json` bij elke launch op van GitHub (weekly scrape). Alleen
app-códewijzigingen vragen een nieuwe build op het toestel.
