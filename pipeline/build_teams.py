"""Bouwt data/teams.json uit de twee bronpagina's plus de handmatige seeds.

Gebruik:
    python3 pipeline/build_teams.py --offline          # parse uit pipeline/snapshots/
    python3 pipeline/build_teams.py                    # live fetch (GitHub Actions)
    opties: --skip-colors --skip-crest-check --out PATH

Stappen: fetch/parse -> dedup sterrenlijst -> league-kopie-drop + assertie ->
join op genormaliseerde naam (+ vrouwenvlag) -> crest/kleur-verrijking ->
national teams seed erbij -> schemaVersion 1 JSON. Elke gedropte of unmatched
rij wordt gelogd; stil weglaten is een bug.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from normalize import is_womens_name, match_name, normalize, slugify, strip_womens_marker
from parse import parse_best_teams, parse_stars

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS = ROOT / "pipeline" / "snapshots"

STARS_URL = "https://fifagamenews.com/fc-26-team-star-ratings/"
BEST_TEAMS_URL = "https://fifauteam.com/best-teams-fc-26/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def log(msg: str) -> None:
    print(msg, flush=True)


def fetch(url: str) -> str:
    import requests

    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    resp.raise_for_status()
    return resp.text


def load_html(offline: bool) -> tuple[str, str]:
    if offline:
        return (
            (SNAPSHOTS / "stars.html").read_text(encoding="utf-8"),
            (SNAPSHOTS / "best-teams.html").read_text(encoding="utf-8"),
        )
    return fetch(STARS_URL), fetch(BEST_TEAMS_URL)


def dedup_stars(star_rows):
    """Dedup op (genormaliseerde naam, vrouwenvlag); hou de eerste (hoogste
    rank / hoogste sterren) en log elke gedropte rij."""
    seen = {}
    kept = []
    for row in star_rows:
        key = (normalize(row.name), is_womens_name(row.name))
        if key in seen:
            log(
                f"DEDUP: drop '{row.name}' ({row.stars}★, rank {row.rank}); "
                f"hou rank {seen[key].rank} met {seen[key].stars}★"
            )
            continue
        seen[key] = row
        kept.append(row)
    return kept


def group_leagues(league_rows, league_meta):
    """Groepeer per league-titel, drop bekende kopie-leagues en assert dat
    geen twee overgebleven leagues een identieke teamlijst hebben."""
    by_title = defaultdict(list)
    for row in league_rows:
        by_title[row.league_title].append(row)

    unknown = set(by_title) - set(league_meta)
    if unknown:
        raise SystemExit(f"FOUT: onbekende league-titels op bronpagina: {sorted(unknown)}")

    for title, meta in league_meta.items():
        if meta.get("drop") and title in by_title:
            log(f"DROP LEAGUE: '{title}' ({meta['drop']}), {len(by_title[title])} rijen")
            del by_title[title]

    rosters = {t: tuple(sorted(normalize(r.name) for r in rows)) for t, rows in by_title.items()}
    by_roster = defaultdict(list)
    for title, roster in rosters.items():
        by_roster[roster].append(title)
    copies = [titles for titles in by_roster.values() if len(titles) > 1]
    if copies:
        raise SystemExit(
            f"FOUT: leagues met identieke teamlijst (nieuwe bronpagina-bug?): {copies}"
        )
    return by_title


def join(star_rows, by_title, league_meta, aliases):
    """Join sterrenrijen aan league-rijen op (genormaliseerde naam, vrouwenvlag)."""
    league_index = {}
    for title, rows in by_title.items():
        meta = league_meta[title]
        for row in rows:
            key = (normalize(row.name), meta["womens"] or is_womens_name(row.name))
            if key in league_index:
                log(f"WAARSCHUWING: league-pagina dubbel: {row.name} in {title}")
                continue
            league_index[key] = (row, meta)

    teams = []
    unmatched = []
    used_keys = set()
    for star in star_rows:
        womens = is_womens_name(star.name)
        star_key = normalize(star.name)
        pool = [k for (k, w) in league_index if w == womens]
        matched, how = match_name(star_key, pool, aliases)
        display = strip_womens_marker(star.name)
        if matched is None:
            unmatched.append((star, how))
            teams.append(
                {
                    "id": f"unk.{slugify(star.name)}" + ("-w" if womens else ""),
                    "name": display,
                    "kind": "club",
                    "womens": womens,
                    "starRating": star.stars,
                    "squadRating": None,
                    "attack": None,
                    "midfield": None,
                    "defence": None,
                    "leagueId": None,
                    "leagueName": None,
                    "countryCode": None,
                    "crestURL": star.crest_url,
                    "primaryColor": None,
                    "secondaryColor": None,
                }
            )
            continue
        row, meta = league_index[(matched, womens)]
        used_keys.add((matched, womens))
        if how != "exact":
            log(f"MATCH ({how}): '{star.name}' -> '{row.name}' [{meta['id']}]")
        teams.append(
            {
                "id": f"{meta['id'].split('.')[0]}.{slugify(star.name)}" + ("-w" if womens else ""),
                "name": display,
                "kind": "club",
                "womens": womens,
                "starRating": star.stars,
                "squadRating": row.squad_rating,
                "attack": None,
                "midfield": None,
                "defence": None,
                "leagueId": meta["id"],
                "leagueName": meta["name"],
                "countryCode": meta["country"],
                "crestURL": row.crest_url or star.crest_url,
                "primaryColor": None,
                "secondaryColor": None,
            }
        )

    for star, how in unmatched:
        log(f"UNMATCHED: '{star.name}' ({star.stars}★) -> league null ({how})")
    for key, (row, meta) in league_index.items():
        if key not in used_keys:
            log(f"ALLEEN OP LEAGUE-PAGINA (geen sterren, niet opgenomen): {row.name} [{meta['id']}]")

    dup_ids = [i for i, c in _count([t["id"] for t in teams]).items() if c > 1]
    if dup_ids:
        raise SystemExit(f"FOUT: dubbele team-ids na join: {dup_ids}")
    return teams


def _count(items):
    out = {}
    for i in items:
        out[i] = out.get(i, 0) + 1
    return out


def upgrade_crests(teams, skip: bool):
    """Bronpagina's linken 15px-crests (…/teams/small/X.webp). Probeer de
    grote variant (…/teams/X.webp) met één sample-check; kleiner risico dan
    660 HEAD-requests en het CMS genereert beide varianten uniform."""
    sample = next((t["crestURL"] for t in teams if t["crestURL"]), None)
    if skip or sample is None or "/small/" not in sample:
        return
    import requests

    large = sample.replace("/small/", "/")
    try:
        ok = (
            requests.head(large, headers={"User-Agent": USER_AGENT}, timeout=30).status_code
            == 200
        )
    except Exception as e:  # noqa: BLE001
        log(f"WAARSCHUWING: crest-check faalde ({e}); hou small-URLs")
        return
    if ok:
        for t in teams:
            if t["crestURL"] and "/small/" in t["crestURL"]:
                t["crestURL"] = t["crestURL"].replace("/small/", "/")
        log(f"CRESTS: grote variant beschikbaar ({large}), alle URLs geüpgraded")
    else:
        log("CRESTS: grote variant niet beschikbaar, hou small-URLs")


def dominant_colors(teams, skip: bool):
    """Haal per team de (kleine) crest op en bepaal een dominante kleur voor
    de fallback-tile, plus wit/zwart als contrastkleur."""
    if skip:
        return
    import requests
    from PIL import Image

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    done = 0
    for t in teams:
        url = t["crestURL"]
        if not url:
            continue
        small = url.replace("/teams/", "/teams/small/") if "/small/" not in url else url
        try:
            resp = session.get(small, timeout=20)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGBA").resize((16, 16))
        except Exception as e:  # noqa: BLE001
            log(f"KLEUR: fetch faalde voor {t['id']} ({e})")
            continue
        best, best_score = None, -1.0
        for r, g, b, a in img.getdata():
            if a < 128:
                continue
            mx, mn = max(r, g, b), min(r, g, b)
            sat = 0 if mx == 0 else (mx - mn) / mx
            score = sat * (mx / 255)
            if score > best_score:
                best_score, best = score, (r, g, b)
        if best is None or best_score < 0.15:
            continue
        r, g, b = best
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        t["primaryColor"] = f"#{r:02X}{g:02X}{b:02X}"
        t["secondaryColor"] = "#FFFFFF" if lum < 160 else "#101010"
        done += 1
    log(f"KLEUR: {done} teams van een fallback-kleur voorzien")


def apply_overrides(teams, path: Path | None = None):
    """Pas handmatige correcties uit pipeline/overrides.json toe (sterren zijn
    leidend, squadRating mag ook). Draait vóór de audit zodat gecorrigeerde
    waarden dezelfde invarianten moeten halen als gescrapete."""
    path = path or ROOT / "pipeline" / "overrides.json"
    if not path.exists():
        return
    rows = json.loads(path.read_text(encoding="utf-8"))["overrides"]
    by_id = {t["id"]: t for t in teams}
    for o in rows:
        team = by_id.get(o["id"])
        if team is None:
            log(f"OVERRIDE WARN: '{o['id']}' niet in dataset — team weg of id gewijzigd; "
                "regel bijwerken of verwijderen")
            continue
        for field in ("starRating", "squadRating"):
            want = o.get(field)
            if want is None:
                continue
            if team[field] == want:
                log(f"OVERRIDE OVERBODIG: {o['id']} {field} is al {want} — "
                    "bron is bijgetrokken, regel kan uit overrides.json")
            else:
                log(f"OVERRIDE: {o['id']} {field} {team[field]} -> {want} "
                    f"({o.get('reason', 'geen reden opgegeven')})")
                team[field] = want


def load_national_teams():
    path = ROOT / "data" / "national-teams.json"
    if not path.exists():
        log("NATIONAL: data/national-teams.json ontbreekt, geen landenteams opgenomen")
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    teams = doc["teams"]
    for t in teams:
        for field in ("id", "name", "starRating", "squadRating"):
            if t.get(field) in (None, ""):
                raise SystemExit(f"FOUT: national team mist '{field}': {t}")
        t.setdefault("kind", "national")
        t.setdefault("womens", False)
        for field in ("attack", "midfield", "defence", "leagueId", "leagueName",
                      "countryCode", "crestURL", "primaryColor", "secondaryColor"):
            t.setdefault(field, None)
        if t["kind"] != "national":
            raise SystemExit(f"FOUT: {t['id']} in national-teams.json is geen national")
    log(f"NATIONAL: {len(teams)} landenteams uit seed")
    return teams


def build(offline: bool, skip_colors: bool, skip_crest_check: bool, out_path: Path) -> None:
    stars_html, best_html = load_html(offline)
    star_rows = parse_stars(stars_html)
    league_rows = parse_best_teams(best_html)
    log(f"PARSE: {len(star_rows)} sterrenrijen, {len(league_rows)} league-rijen")

    league_meta = json.loads((ROOT / "pipeline" / "leagues.json").read_text(encoding="utf-8"))[
        "leagues"
    ]
    aliases = json.loads((ROOT / "pipeline" / "aliases.json").read_text(encoding="utf-8"))[
        "aliases"
    ]

    star_rows = dedup_stars(star_rows)
    by_title = group_leagues(league_rows, league_meta)
    teams = join(star_rows, by_title, league_meta, aliases)
    upgrade_crests(teams, skip_crest_check)
    dominant_colors(teams, skip_colors)
    teams += load_national_teams()
    apply_overrides(teams)

    matched = sum(1 for t in teams if t["leagueId"])
    log(f"RESULTAAT: {len(teams)} teams, {matched} met league")

    from audit import run_audit
    run_audit(teams, log)

    payload = {
        "schemaVersion": 1,
        "game": "FC 26",
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "leagues": [
            {
                "id": m["id"],
                "name": m["name"],
                "countryCode": m["country"],
                "womens": m["womens"],
                "defaultWhitelist": m["defaultWhitelist"],
            }
            for title, m in league_meta.items()
            if not m.get("drop") and title in by_title
        ],
        "teams": teams,
    }

    if out_path.exists():
        old = json.loads(out_path.read_text(encoding="utf-8"))
        if {k: v for k, v in old.items() if k != "generatedAt"} == {
            k: v for k, v in payload.items() if k != "generatedAt"
        }:
            log("GEEN DIFF: inhoud ongewijzigd, bestand niet aangeraakt")
            return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"GESCHREVEN: {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="parse uit pipeline/snapshots/")
    ap.add_argument("--skip-colors", action="store_true")
    ap.add_argument("--skip-crest-check", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "teams.json")
    args = ap.parse_args()
    build(args.offline, args.skip_colors, args.skip_crest_check, args.out)
