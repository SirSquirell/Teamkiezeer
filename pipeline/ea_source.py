"""FC 27-bron: EA's eigen ratingsite voor clubs en competities, plus een
gecommit sterrenbestand.

Waarom niet de oude twee bronpagina's: fifagamenews' FC 27-sterren zijn een
formule op fifauteams teamratings van seizoen 2025/26 (zie
docs/data-audit-fc27.md). EA's ratingsite is wél de echte FC 27-database: per
competitie de clubs (ratingsFilters.teamGroups in __NEXT_DATA__), met
mannen/vrouwen per groep. Sterren publiceert EA daar niet; die komen uit
pipeline/stars-fc27.json, waar per club staat waar de waarde vandaan komt.
"""

from __future__ import annotations

import json
import re

from normalize import slugify

NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def parse_ea_groups(html: str) -> list[dict]:
    m = NEXT_DATA.search(html)
    if m is None:
        raise ValueError("EA-ratings: geen __NEXT_DATA__, structuur veranderd?")
    data = json.loads(m.group(1))
    try:
        groups = data["props"]["pageProps"]["ratingsFilters"]["teamGroups"]
    except (KeyError, TypeError) as e:
        raise ValueError(f"EA-ratings: teamGroups ontbreekt ({e})") from e
    out = []
    for g in groups:
        gender = (g.get("gender") or {}).get("id")
        if gender not in (0, 1):
            raise ValueError(f"EA-ratings: groep {g.get('label')} zonder geslacht")
        seen = set()
        teams = []
        for t in g.get("teams") or []:
            # EA zet een paar clubs twee keer in dezelfde groep.
            if t["id"] in seen:
                continue
            seen.add(t["id"])
            teams.append({"eaId": int(t["id"]), "name": " ".join(str(t["label"]).split()),
                          "crestURL": t.get("imageUrl")})
        out.append({"eaId": str(g["id"]), "name": g["label"], "womens": gender == 1,
                    "teams": teams})
    if sum(len(g["teams"]) for g in out) < 500:
        raise ValueError("EA-ratings: verdacht weinig clubs, structuur veranderd?")
    return out


def build_ea_teams(groups: list[dict], mapping: dict, stars: dict, log):
    """Bouw teams en leagues. Een club zonder ster in stars-fc27.json komt er
    niet in (gelogd); een EA-groep die niet in de mapping staat en geen
    Rest of World-groepje is, laat de build falen."""
    row = mapping["restOfWorld"]
    metas = {}
    for g in groups:
        meta = mapping["groups"].get(g["eaId"])
        if meta is None:
            if len(g["teams"]) > row["maxTeams"]:
                raise SystemExit(f"FOUT: onbekende EA-competitie '{g['name']}' "
                                 f"({len(g['teams'])} clubs); voeg toe aan ea-leagues-fc27.json")
            meta = row["women" if g["womens"] else "men"]
        metas[g["eaId"]] = dict(meta, womens=g["womens"])

    # Een club in twee groepen (CONMEBOL-clubs) telt in de eerste echte
    # competitie, niet in een Rest of World-groepje.
    order = sorted(groups, key=lambda g: metas[g["eaId"]]["id"].startswith("row."))
    teams, used, ids = [], set(), set()
    missing = []
    clubs = stars["clubs"]
    for g in order:
        meta = metas[g["eaId"]]
        for t in g["teams"]:
            if t["eaId"] in used:
                continue
            used.add(t["eaId"])
            s = clubs.get(str(t["eaId"]))
            if s is None or s.get("stars") is None:
                missing.append(f"{t['name']} [{g['name']}]")
                continue
            base = f"{meta['id'].split('.')[0]}.{slugify(t['name'])}" + ("-w" if g["womens"] else "")
            tid = base if base not in ids else f"{base}-{t['eaId']}"
            ids.add(tid)
            teams.append({
                "id": tid,
                "name": t["name"],
                "kind": "club",
                "womens": g["womens"],
                "starRating": float(s["stars"]),
                "squadRating": s.get("ovr"),
                "attack": s.get("att"),
                "midfield": s.get("mid"),
                "defence": s.get("def"),
                "leagueId": meta["id"],
                "leagueName": meta["name"],
                "countryCode": meta["country"],
                "crestURL": t["crestURL"],
                "primaryColor": None,
                "secondaryColor": None,
            })
    for m in missing:
        log(f"EA: geen ster in stars-fc27.json, niet opgenomen: {m}")
    leagues, seen = [], set()
    for g in groups:
        meta = metas[g["eaId"]]
        if meta["id"] in seen or not any(t["leagueId"] == meta["id"] for t in teams):
            continue
        seen.add(meta["id"])
        leagues.append({"id": meta["id"], "name": meta["name"], "countryCode": meta["country"],
                        "womens": meta["womens"],
                        "defaultWhitelist": bool(meta.get("defaultWhitelist", False))})
    log(f"EA: {len(used)} clubs bij EA, {len(teams)} met ster, {len(missing)} zonder, "
        f"{len(leagues)} competities")
    return teams, leagues
