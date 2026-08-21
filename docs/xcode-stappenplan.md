# De app via de kabel op je iPhone — klik voor klik

Voor deze route hoef je géén developer te zijn. Je volgt de stappen één keer
(reken op een uurtje, vooral wachten op de Xcode-download); daarna kost een
herinstallatie 2 minuten.

**Nodig:** een Mac (macOS 14 of nieuwer), je iPhone (iOS 17+), de
oplaadkabel, je gewone Apple ID. Geen betaald account.

## Deel 1 — eenmalige voorbereiding (Mac)

1. **Xcode installeren.** Open de App Store op de Mac → zoek "Xcode" →
   *Download* (gratis, ±10 GB — zet koffie). Open Xcode één keer: ga akkoord
   met de voorwaarden en klik *Install* als hij om "additional components"
   of "iOS platform support" vraagt.
2. **Project downloaden.** Ga naar
   https://github.com/SirSquirell/Teamkiezeer → groene knop **Code** →
   **Download ZIP** → dubbelklik de ZIP in je Downloads-map om uit te pakken.
3. **Project openen.** Open de uitgepakte map → map `app` → dubbelklik
   **Teamkiezeer.xcodeproj**. Xcode start en laadt even ("Resolving
   packages" onderin — gewoon wachten).
4. **Apple ID koppelen.** Menubalk: **Xcode → Settings… → Accounts** → klik
   linksonder op **+** → *Apple Account* → log in met je Apple ID. Sluit het
   venster.
5. **Handtekening instellen.** Klik in de linkerkolom helemaal bovenaan op
   het blauwe **Teamkiezeer**-icoon → kies in het midden onder *TARGETS*
   **Teamkiezeer** → tab **Signing & Capabilities** → zet bij **Team** de
   dropdown op **"Jouw Naam (Personal Team)"**.
   - Zie je een rode melding over de *bundle identifier*? Verander in het
     veld **Bundle Identifier** `nl.mathijs.teamkiezeer` in iets dat alleen
     jij gebruikt, bijv. `nl.jouwachternaam.teamkiezeer`. Melding weg = goed.

## Deel 2 — de iPhone

6. **Kabel erin.** iPhone met de kabel aan de Mac. Op de iPhone verschijnt
   *"Vertrouw deze computer?"* → **Vertrouw** → toegangscode invoeren.
7. **Ontwikkelaarsmodus aan.** Op de iPhone: **Instellingen → Privacy en
   beveiliging** → helemaal onderaan **Ontwikkelaarsmodus** → aanzetten →
   telefoon herstart → na de herstart bevestigen.
   - Staat die optie er niet? Hij verschijnt pas nadat de iPhone één keer
     aan Xcode heeft gehangen; doe stap 8 en kijk dan nog eens.
8. **Telefoon kiezen in Xcode.** Bovenin het Xcode-venster, naast de
   ▶-knop, staat een apparaat-keuzemenu (waarschijnlijk "Any iOS Device").
   Klik erop en kies **jouw iPhone**. De eerste keer zegt Xcode even
   "Preparing device" — wachten tot dat weg is.

## Deel 3 — installeren

9. **Run.** Klik op de **▶**-knop linksboven (of ⌘R). De eerste build duurt
   1–3 minuten. Daarna staat **Gelijkspel** op je telefoon (het project heet technisch nog Teamkiezeer; het icoon en de naam op je beginscherm zijn Gelijkspel).
10. **App vertrouwen (alleen de eerste keer).** Start de app; zegt iOS
    *"Niet-vertrouwde ontwikkelaar"*? Ga naar **Instellingen → Algemeen →
    VPN en apparaatbeheer** → tik onder *Ontwikkelaarsapp* op je Apple ID →
    **Vertrouw** → **Sta toe**. Open de app opnieuw. Klaar — kabel mag eruit.

## Daarna

- **De app stopt na 7 dagen** (beperking van een gratis Apple ID; hij zegt
  dan "app niet langer beschikbaar"). Oplossing: telefoon aan de kabel,
  Xcode open, ▶. Twee minuten.
- **Zonder kabel opnieuw installeren:** na de eerste kabelsessie kun je in
  Xcode via **Window → Devices and Simulators** bij je iPhone *"Connect via
  network"* aanvinken — daarna werkt ▶ ook via wifi.
- **Teamdata is nooit een reden om opnieuw te installeren**: die haalt de
  app zelf wekelijks op.

## Als het hapert

| Melding / probleem | Oplossing |
| --- | --- |
| "Could not launch" | Stap 10 (vertrouwen) nog doen |
| Rode fout over *bundle identifier* | Stap 5: maak de identifier uniek |
| iPhone verschijnt niet in het menu | Telefoon ontgrendelen, andere kabel/poort proberen |
| "Preparing device" blijft lang staan | Gewoon laten staan; eerste keer kan minuten duren |
| "Untrusted Developer" popup | = stap 10 |
| Build-fout na een projectupdate | Verse ZIP downloaden en opnieuw openen |
