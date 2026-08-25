"""Audit op de trekkingskansen van de engine — niet op de data.

Beantwoordt één vraag: hoe vaak kan elk team, elke league en elk land
werkelijk vallen bij een gegeven filterstand? Draait analytisch (exacte
kansen, geen steekproef) op `data/teams.json`.

    python pipeline/draw_audit.py                       # web-defaults (vaste ster 4)
    python pipeline/draw_audit.py --stars any           # "Verras ons"
    python pipeline/draw_audit.py --engine ios --leagues top

Twee engines, want de clients trekken niet hetzelfde:
- `web`  (index.html): kies een (soort, ster)-bucket gewogen naar grootte,
         dan twee teams uniform. Geen ratinggrens.
- `ios`  (TeamkiezeerKit/DrawEngine): zelfde bucketkeuze, maar daarna
         uniform over de *geldige paren* binnen `maxRatingDelta`.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOP_LEAGUES = None  # gevuld uit de dataset (defaultWhitelist), = de iOS-default


def load() -> dict:
    return json.loads((ROOT / "data" / "teams.json").read_text(encoding="utf-8"))


def build_pool(doc: dict, stars, kind: str, womens: bool, whitelist: set[str]) -> list[dict]:
    out = []
    for t in doc["teams"]:
        if t.get("squadRating") is None:
            continue
        if t.get("womens") and not womens:
            continue
        if kind == "clubs" and t["kind"] != "club":
            continue
        if kind == "nats" and t["kind"] != "national":
            continue
        if t["kind"] == "club" and t.get("leagueId") not in whitelist:
            continue
        if stars is not None and t["starRating"] != stars:
            continue
        out.append(t)
    return out


def buckets_of(pool: list[dict]) -> dict:
    b = defaultdict(list)
    for t in pool:
        b[(t["kind"], t["starRating"])].append(t)
    return b


def web_probabilities(pool: list[dict]) -> dict[str, float]:
    """Kans dat een team één van de twee kaarten vult, per draw.

    De bucket weegt naar grootte (n/N) en binnen de bucket is elk team
    even vaak aan de beurt (2/n) — dat valt tegen elkaar weg, dus elk
    trekbaar team zit op 2/N. Buckets met één team vallen eruit.
    """
    b = buckets_of(pool)
    viable = {k: v for k, v in b.items() if len(v) >= 2}
    total = sum(len(v) for v in viable.values())
    p = {t["id"]: 0.0 for t in pool}
    for teams in viable.values():
        for t in teams:
            p[t["id"]] = (len(teams) / total) * (2 / len(teams))
    return p


def ios_probabilities(pool: list[dict], max_delta: int) -> dict[str, float]:
    """Idem, maar uniform over de geldige paren in de bucket.

    Daardoor telt hoeveel tegenstanders een team heeft: wie met zijn
    squad rating aan de rand van zijn sterbucket zit, heeft er minder en
    valt navenant minder vaak. Alleen trap 0 van de versoepelingsladder:
    zolang er ergens in de pool één geldig paar is, komt de engine nooit
    aan trap 1 toe.
    """
    b = buckets_of(pool)
    weighed, total = [], 0
    for key in sorted(b, key=str):
        teams = sorted(b[key], key=lambda t: t["id"])
        if len(teams) < 2:
            continue
        pairs = [
            (x, y)
            for x, y in combinations(teams, 2)
            if abs(x["squadRating"] - y["squadRating"]) <= max_delta
        ]
        if not pairs:
            continue
        weighed.append((teams, pairs))
        total += len(teams)
    p = {t["id"]: 0.0 for t in pool}
    for teams, pairs in weighed:
        deg = Counter()
        for x, y in pairs:
            deg[x["id"]] += 1
            deg[y["id"]] += 1
        for t in teams:
            p[t["id"]] = (len(teams) / total) * (deg[t["id"]] / len(pairs))
    return p


def never_prob(pool, p, predicate, draws: int) -> float:
    """Kans dat geen enkele draw in `draws` een team met `predicate` oplevert.

    Benadering: de twee kaarten van één draw zitten in dezelfde bucket en
    zijn dus niet onafhankelijk, maar voor het orde-van-grootte-antwoord
    ("kan dit toeval zijn?") is (1 - kans per kaart) ** (2 * draws) scherp
    genoeg.
    """
    share = sum(p[t["id"]] for t in pool if predicate(t)) / 2
    return (1 - share) ** (2 * draws)


def report(doc, pool, p, args) -> None:
    n_reach = sum(1 for t in pool if p[t["id"]] > 0)
    print(f"pool: {len(pool)} teams, waarvan {n_reach} ooit trekbaar")
    if not n_reach:
        print("  LEEG — geen enkele bucket heeft twee teams.")
        return
    uniform = 2 / n_reach

    lg = Counter()
    for t in pool:
        lg[t.get("leagueName") or "Landenteams"] += p[t["id"]] / 2
    print("\nkans per league (aandeel van alle getrokken kaarten):")
    for name, share in lg.most_common():
        cnt = sum(1 for t in pool if (t.get("leagueName") or "Landenteams") == name)
        print(f"  {100 * share:5.1f}%  ({cnt:3d} teams)  {name}")

    land = Counter()
    for t in pool:
        key = (t.get("leagueId") or "??").split(".")[0].upper() if t["kind"] == "club" else "LANDEN"
        land[key] += p[t["id"]] / 2
    print("\nkans per land-blok:")
    for key, share in land.most_common(8):
        print(f"  {100 * share:5.1f}%  {key}")

    dead = [t for t in pool if p[t["id"]] == 0]
    if dead:
        print(f"\nNOOIT trekbaar ({len(dead)}):")
        for t in dead:
            print(f"  {t['name']} — {t['starRating']}* rating {t['squadRating']} ({t.get('leagueName')})")

    ranked = sorted((t for t in pool if p[t["id"]] > 0), key=lambda t: p[t["id"]])
    spread = p[ranked[-1]["id"]] / p[ranked[0]["id"]]
    print(f"\nspreiding tussen trekbare teams: {spread:.2f}x (1.00x = perfect eerlijk)")
    if spread > 1.01:
        for label, rows in (("minst", ranked[:5]), ("meest", ranked[-5:])):
            print(f"  {label} waarschijnlijk:")
            for t in rows:
                print(f"    {100 * p[t['id']] / 2:5.2f}%  ({p[t['id']] / uniform:.2f}x)  "
                      f"{t['name']} {t['starRating']}* r{t['squadRating']}")

    draws = args.draws
    distinct = n_reach * (1 - (1 - 1 / n_reach) ** (2 * draws))
    print(f"\nin {draws} draws ({2 * draws} kaarten) verwacht je ~{distinct:.0f} verschillende "
          f"teams; {2 * draws - distinct:.0f} kaarten zijn dus een herhaling")

    print("\nkans dat een league in die {} draws 0x valt:".format(draws))
    for lid, name in [("eng.1", "Premier League"), ("fra.1", "Ligue 1"),
                      ("esp.1", "LaLiga"), ("ita.1", "Serie A"), ("ger.1", "Bundesliga")]:
        q = never_prob(pool, p, lambda t, lid=lid: t.get("leagueId") == lid, draws)
        print(f"  {100 * q:6.2f}%  {name}")


def main() -> None:
    doc = load()
    top = {l["id"] for l in doc["leagues"] if l.get("defaultWhitelist")}
    allw = {l["id"] for l in doc["leagues"]}

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", choices=["web", "ios"], default="web")
    ap.add_argument("--stars", default="4", help='vaste ster (bv. 4 of 3.5) of "any" voor Verras ons')
    ap.add_argument("--kind", choices=["mixed", "clubs", "nats"], default="mixed")
    ap.add_argument("--leagues", choices=["all", "top"], default="all",
                    help="all = de web-default (alles aan), top = de iOS-default")
    ap.add_argument("--womens", action="store_true")
    ap.add_argument("--max-delta", type=int, default=2, help="alleen voor --engine ios")
    ap.add_argument("--draws", type=int, default=20)
    args = ap.parse_args()

    stars = None if args.stars == "any" else float(args.stars)
    whitelist = allw if args.leagues == "all" else top
    pool = build_pool(doc, stars, args.kind, args.womens, whitelist)

    print(f"engine={args.engine}  ster={args.stars}  soort={args.kind}  "
          f"leagues={args.leagues} ({len(whitelist)})  vrouwen={args.womens}")
    p = web_probabilities(pool) if args.engine == "web" else ios_probabilities(pool, args.max_delta)
    report(doc, pool, p, args)


if __name__ == "__main__":
    main()
