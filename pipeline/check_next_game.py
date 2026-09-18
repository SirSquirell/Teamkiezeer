"""Kijkt of de opvolgende EA-titel écht eigen sterren heeft, of nog de tabel
van de huidige titel toont.

Waarom dit bestaat: fifagamenews publiceert de pagina van een nieuwe titel
weken voor de echte ratings landen, gevuld met een kopie van het vorige jaar.
Op 2026-09-18 gaf `/fc-27-team-star-ratings/` netjes een 200 met 661 rijen,
identiek aan FC 26 tot op de halve ster, met een dateModified van 2026-05-18.
Een 200 op de URL is dus geen bewijs dat de data er is; het verschil met de
huidige dataset is dat wel.

Gebruik:
    python3 pipeline/check_next_game.py              # live fetch, print verdict
    python3 pipeline/check_next_game.py --stars PAD  # toets een lokaal bestand

Faalt nooit hard: dit is een signaal naast de databuild, geen poortwachter.
Een netwerkfout logt en geeft verdict 'onbekend'.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from normalize import is_womens_name, normalize, strip_womens_marker
from parse import parse_stars

ROOT = Path(__file__).resolve().parent.parent

# Onder deze grens is het een kopie. EA schuift tussen twee titels tientallen
# tot honderden clubs op; een handvol verschillen is een correctie op de oude
# pagina, geen nieuw seizoen. 10 ligt ruim boven die ruis en ruim onder een
# echte seizoenswissel.
DRIFT_DREMPEL = 10


def log(msg: str) -> None:
    print(msg, flush=True)


def sterren_uit_dataset(path: Path) -> dict[tuple[str, bool], float]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {
        (normalize(t["name"]), bool(t["womens"])): t["starRating"]
        for t in doc["teams"]
        if t["kind"] == "club"
    }


def sterren_uit_pagina(html: str) -> dict[tuple[str, bool], float]:
    uit: dict[tuple[str, bool], float] = {}
    for rij in parse_stars(html):
        sleutel = (normalize(strip_womens_marker(rij.name)), is_womens_name(rij.name))
        uit.setdefault(sleutel, rij.stars)
    return uit


def vergelijk(nieuw: dict, huidig: dict) -> dict:
    gedeeld = set(nieuw) & set(huidig)
    afwijkend = [k for k in gedeeld if nieuw[k] != huidig[k]]
    return {
        "rijen_nieuw": len(nieuw),
        "rijen_huidig": len(huidig),
        "gedeeld": len(gedeeld),
        "alleen_nieuw": len(set(nieuw) - set(huidig)),
        "alleen_huidig": len(set(huidig) - set(nieuw)),
        "afwijkend": len(afwijkend),
        "voorbeelden": sorted(
            (f"{n}{' (W)' if w else ''}: {huidig[(n, w)]}* -> {nieuw[(n, w)]}*")
            for n, w in afwijkend
        )[:10],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stars", type=Path, help="lokaal HTML-bestand i.p.v. live fetch")
    args = ap.parse_args()

    doc = json.loads((ROOT / "pipeline" / "games.json").read_text(encoding="utf-8"))
    huidig_id, volgend_id = doc["current"], doc.get("next")
    if not volgend_id:
        log("Geen 'next' in games.json; niets te controleren.")
        return 0
    volgend = doc["games"][volgend_id]
    huidig_pad = ROOT / doc["games"][huidig_id]["out"]
    if not huidig_pad.exists():
        log(f"Huidige dataset {huidig_pad} ontbreekt; kan niet vergelijken.")
        return 0

    log(f"CHECK: {volgend_id} ({volgend['label']}) tegen {huidig_id} ({huidig_pad.name})")
    if args.stars:
        html = args.stars.read_text(encoding="utf-8")
    else:
        try:
            from build_teams import fetch

            html = fetch(volgend["starsURL"])
        except Exception as e:  # noqa: BLE001
            log(f"ONBEKEND: fetch van {volgend['starsURL']} faalde ({e})")
            schrijf_output(status="onbekend")
            return 0

    try:
        nieuw = sterren_uit_pagina(html)
    except Exception as e:  # noqa: BLE001
        # Een structuurwijziging is zelf nieuws: de pagina is verbouwd.
        log(f"ONBEKEND: {volgend['starsURL']} parseert niet ({e}) — bron verbouwd?")
        schrijf_output(status="onbekend")
        return 0

    r = vergelijk(nieuw, sterren_uit_dataset(huidig_pad))
    log(
        f"  {r['rijen_nieuw']} rijen op de {volgend['label']}-pagina, "
        f"{r['rijen_huidig']} clubs in {huidig_pad.name}, {r['gedeeld']} gedeeld"
    )
    log(f"  nieuw: {r['alleen_nieuw']}, verdwenen: {r['alleen_huidig']}, "
        f"andere sterren: {r['afwijkend']} (drempel {DRIFT_DREMPEL})")

    if r["afwijkend"] >= DRIFT_DREMPEL:
        log(f"LIVE: {volgend['label']} heeft eigen sterren. Voorbeelden:")
        for v in r["voorbeelden"]:
            log(f"    {v}")
        log(f"Overstappen: zet 'current' in games.json op '{volgend_id}', trek verse "
            "snapshots, hertoets de ankers in audit.py en valideer de landenteam-seed.")
        schrijf_output(status="live", **r)
        return 0

    log(f"KOPIE: de {volgend['label']}-pagina toont nog de {doc['games'][huidig_id]['label']}-tabel. "
        "Niets doen.")
    schrijf_output(status="kopie", **r)
    return 0


def schrijf_output(**kv) -> None:
    """Zet de uitkomst in GITHUB_OUTPUT zodat de workflow erop kan sturen."""
    pad = os.environ.get("GITHUB_OUTPUT")
    if not pad:
        return
    with open(pad, "a", encoding="utf-8") as fh:
        for k, v in kv.items():
            if k != "voorbeelden":
                fh.write(f"{k}={v}\n")


if __name__ == "__main__":
    raise SystemExit(main())
