"""Wekelijkse in-game-vorm voor FC 27: haalt alle selecties van EA's
ratingsite, berekent per club de team-OVR en houdt de geschiedenis bij.

Vorm = verschil in berekende team-OVR met de vorige meting waarin iets
veranderde. Zolang EA niets bijwerkt, schuift alleen 'checked' op en groeit
de geschiedenis niet.

Uitvoer:
  pipeline/squads/ea-squads-fc27.json  laatste selecties (één club per regel,
                                        zodat de git-diff per week leesbaar is)
  data/form-fc27.json                  geschiedenis en huidige vorm per club

Gebruik:
  python pipeline/ea_form.py                 live ophalen
  python pipeline/ea_form.py --squads F.json  bestaande ophaal-dump gebruiken
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from team_rating import rate

ROOT = Path(__file__).resolve().parent.parent
SQUADS_OUT = ROOT / "pipeline" / "squads" / "ea-squads-fc27.json"
FORM_OUT = ROOT / "data" / "form-fc27.json"
GAME = "fc27"
# Versie van het model in team_rating.py. Een nieuwe versie start een nieuwe
# baseline: OVR's van twee modellen vergelijken zou nepvorm geven.
MODEL = 1

UITLEG = [
    "In-game vorm per FC 27-club op EA-id, wekelijks uit EA's ratingsite (pipeline/ea_form.py).",
    "history: alleen metingen waarin minstens één club een andere team-OVR kreeg; 'checked' is de laatste controle.",
    "form.<id>.ovr: berekende team-OVR (beste elftal, gewogen lijnen; zie pipeline/team_rating.py).",
    "form.<id>.delta: verschil met de vorige meting in history; sinceBaseline: verschil met de eerste.",
    "Absoluut is het model gemiddeld ~0,5 OVR naast de echte waarde; het verschil tussen weken is nauwkeuriger, want dezelfde fout zit aan beide kanten.",
]


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def write_squads(squads: dict, fetched: str, path: Path = SQUADS_OUT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted(squads, key=int)
    lines = [f' "{k}": {json.dumps(squads[k], separators=(",", ":"))}' for k in keys]
    path.write_text('{"fetched": "%s", "squads": {\n%s\n}}\n' % (fetched, ",\n".join(lines)))


def team_ovrs(squads: dict) -> dict[str, float]:
    out = {}
    for tid, squad in squads.items():
        if len(squad) < 11:
            log(f"club {tid}: maar {len(squad)} spelers, overgeslagen")
            continue
        out[tid] = round(rate(squad)["ovr"], 1)
    return out


def update_form(previous: dict | None, ovrs: dict[str, float], today: str) -> dict:
    if previous and previous.get("model") != MODEL:
        previous = None
    history = list((previous or {}).get("history") or [])
    if not history or history[-1]["ovr"] != ovrs:
        history.append({"date": today, "ovr": ovrs})
    last = history[-1]["ovr"]
    prev = history[-2]["ovr"] if len(history) > 1 else last
    base = history[0]["ovr"]
    form = {}
    for tid, ovr in sorted(last.items(), key=lambda kv: int(kv[0])):
        form[tid] = {
            "ovr": ovr,
            "delta": round(ovr - prev.get(tid, ovr), 1),
            "sinceBaseline": round(ovr - base.get(tid, ovr), 1),
        }
    return {
        "_uitleg": UITLEG,
        "game": GAME,
        "model": MODEL,
        "checked": today,
        "baseline": history[0]["date"],
        "form": form,
        "history": history,
    }


def write_form(doc: dict, path: Path = FORM_OUT) -> None:
    # Eén regel per club en per meting: de wekelijkse git-diff toont precies wie bewoog.
    form = ",\n".join(f'  "{k}": {json.dumps(v, separators=(",", ":"))}' for k, v in doc["form"].items())
    hist = ",\n".join("  " + json.dumps(h, separators=(",", ":")) for h in doc["history"])
    head = {k: v for k, v in doc.items() if k not in ("form", "history")}
    text = json.dumps(head, indent=1, ensure_ascii=False)
    path.write_text(text[:-2] + ',\n "form": {\n' + form + '\n },\n "history": [\n' + hist + "\n ]\n}\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--squads", help="ophaal-dump ({squads, failed, fetched}) i.p.v. live")
    args = ap.parse_args(argv)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if args.squads:
        dump = json.loads(Path(args.squads).read_text())
    else:
        import requests

        from build_teams import USER_AGENT, resolve_game
        from ea_source import parse_ea_groups
        from ea_squads import fetch_squads

        _, game = resolve_game(GAME)
        url = game["eaRatingsURL"]
        html = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60).text
        ids = sorted({t["eaId"] for g in parse_ea_groups(html) for t in g["teams"]})
        log(f"{len(ids)} clubs ophalen")
        dump = fetch_squads(url, ids, USER_AGENT, log)
        dump["fetched"] = today

    squads, failed = dump["squads"], dump.get("failed") or []
    if failed:
        log(f"{len(failed)} clubs mislukt: {failed[:20]}")
    # Een halve meting zou als vormverlies of -winst lezen: liever niets schrijven.
    if len(failed) > 0.02 * (len(squads) + len(failed)):
        log("te veel mislukte clubs, niets geschreven")
        return 1

    ovrs = team_ovrs(squads)
    previous = json.loads(FORM_OUT.read_text()) if FORM_OUT.exists() else None
    if previous and previous.get("model") == MODEL:
        # Een club die deze week mislukte houdt zijn vorige waarde.
        for tid, ovr in previous["history"][-1]["ovr"].items():
            ovrs.setdefault(tid, ovr)
    doc = update_form(previous, ovrs, today)
    write_squads(squads, dump.get("fetched", today))
    write_form(doc)
    moved = {k: v for k, v in doc["form"].items() if v["delta"]}
    log(f"{len(doc['form'])} clubs, {len(moved)} met andere team-OVR dan de vorige meting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
