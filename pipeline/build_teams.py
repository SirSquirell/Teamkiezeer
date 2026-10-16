"""Bouwt data/teams.json uit de twee bronpagina's plus de handmatige seeds.

Gebruik:
    python3 pipeline/build_teams.py --offline          # parse uit pipeline/snapshots/
    python3 pipeline/build_teams.py                    # live fetch (GitHub Actions)
    opties: --skip-colors --skip-crest-check --out PATH --game ID

Welke EA-titel er gebouwd wordt komt uit pipeline/games.json ('current', tenzij
--game iets anders zegt); daar staan ook de bron-URL's en het uitvoerpad.

Stappen: fetch/parse -> dedup sterrenlijst -> league-kopie-drop + assertie ->
join op genormaliseerde naam (+ vrouwenvlag) -> crest/kleur-verrijking ->
national teams seed erbij -> schemaVersion 1 JSON. Elke gedropte of unmatched
rij wordt gelogd; stil weglaten is een bug.
"""

from __future__ import annotations

import argparse
import difflib
import io
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from normalize import is_womens_name, match_name, normalize, slugify, strip_womens_marker
from parse import crest_key, parse_best_teams, parse_roster, parse_stars

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS = ROOT / "pipeline" / "snapshots"

GAMES_PATH = ROOT / "pipeline" / "games.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def load_games() -> dict:
    """De titel-config (pipeline/games.json). Eén plek voor label, bron-URL's
    en uitvoerpad per EA-titel; hardcode een game hier niet omheen."""
    return json.loads(GAMES_PATH.read_text(encoding="utf-8"))


def resolve_game(game_id: str | None) -> tuple[str, dict]:
    """Geef (id, config) voor de gevraagde titel, of voor 'current' als er geen
    is opgegeven. Een onbekende id faalt luid; stil op de verkeerde titel
    bouwen is precies de fout die deze config moet voorkomen."""
    doc = load_games()
    game_id = game_id or doc["current"]
    if game_id not in doc["games"]:
        raise SystemExit(
            f"FOUT: onbekende game '{game_id}'; games.json kent {sorted(doc['games'])}"
        )
    return game_id, doc["games"][game_id]


def log(msg: str) -> None:
    print(msg, flush=True)


def fetch(url: str) -> str:
    import requests

    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    resp.raise_for_status()
    return resp.text


def load_html(offline: bool, game: dict) -> tuple[str, str]:
    if offline:
        return (
            (SNAPSHOTS / "stars.html").read_text(encoding="utf-8"),
            (SNAPSHOTS / "best-teams.html").read_text(encoding="utf-8"),
        )
    return fetch(game["starsURL"]), fetch(game["bestTeamsURL"])


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

    rosters = {t: tuple(sorted(normalize(r.name) for r in rows)) for t, rows in by_title.items()}
    # Alleen droppen als de kopie er nu ook echt staat: de FC 26-pagina heeft
    # de bug, de FC 27-pagina niet, en leagues.json geldt voor beide.
    for title, meta in league_meta.items():
        if not (meta.get("drop") and title in by_title):
            continue
        if any(rosters[title] == r for t, r in rosters.items() if t != title):
            log(f"DROP LEAGUE: '{title}' ({meta['drop']}), {len(by_title[title])} rijen")
            del by_title[title]
            del rosters[title]
        else:
            log(f"KOPIE-BUG WEG: '{title}' heeft een eigen teamlijst, league blijft erin")
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
    # Beide bronnen linken dezelfde fifauteam-crests. Een crest die precies
    # één league-rij heeft is een betere sleutel dan fuzzy op naam
    # ("Villarreal CF" vs "Villareal"); een gedeelde crest (Sporting CP en
    # Real Sporting) beslist niets en valt terug op de naam.
    by_crest = defaultdict(list)
    for key, (row, _meta) in league_index.items():
        ck = crest_key(row.crest_url)
        if ck:
            by_crest[(ck, key[1])].append(key[0])

    # Een league-rij die al een sterrenrij met exact dezelfde naam heeft, is
    # bezet; anders koppelt de crest het FC 26-vrouwenteam "Nantes" (zonder
    # (W) op de bron) aan de mannen van "FC Nantes".
    exact = {(normalize(s.name), is_womens_name(s.name)) for s in star_rows} & set(league_index)

    teams = []
    unmatched = []
    used_keys = set()
    for star in star_rows:
        womens = is_womens_name(star.name)
        star_key = normalize(star.name)
        pool = [k for (k, w) in league_index if w == womens]
        matched, how = match_name(star_key, pool, aliases)
        if how not in ("exact", "alias"):
            via_crest = [k for k in by_crest.get((crest_key(star.crest_url), womens), [])
                         if (k, womens) not in exact]
            if len(via_crest) == 1:
                matched, how = via_crest[0], "crest"
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


ROSTER_WOMENS = ("WOMEN", "FEMALE", "FRAUEN", "LIGA F", "NWSL", "ARKEMA")


def roster_check(teams, roster_rows, aliases: dict[str, str]) -> set[str]:
    """Leg de clubs naast de officiële teamlijst van de titel en geef de ids
    terug van clubs die er niet op staan. Een club op de teamlijst zonder ster
    op de bron wordt alleen gelogd: zonder ster kunnen we hem niet eerlijk
    loten."""
    clubs = [t for t in teams if t["kind"] == "club"]
    by_id = {t["id"]: t for t in clubs}
    by_name = {(normalize(t["name"]), t["womens"]): t for t in clubs}
    by_crest = defaultdict(list)
    for t in clubs:
        if crest_key(t["crestURL"]):
            by_crest[(crest_key(t["crestURL"]), t["womens"])].append(t)
    seen = set()
    rest = []
    for row in roster_rows:
        womens = any(w in row.league_title for w in ROSTER_WOMENS)
        hit = by_name.get((normalize(row.name), womens))
        if hit is None:
            cands = by_crest.get((crest_key(row.crest_url), womens), [])
            hit = cands[0] if len(cands) == 1 and cands[0]["id"] not in seen else None
        if hit is None:
            rest.append((row, womens))
        else:
            seen.add(hit["id"])
    # Tweede ronde op wat overblijft: een handmatige koppeling (aliases.json,
    # 'teamlijst'), of dezelfde crest, of de ene naam bevat de andere
    # ("Celta" / "Celta Vigo"), of bijna dezelfde spelling. Alleen bij precies
    # één kandidaat.
    missing = []
    for row, womens in rest:
        rk = normalize(row.name)
        alias = aliases.get(rk + (" w" if womens else ""))
        if alias in by_id and alias not in seen:
            seen.add(alias)
            continue
        rt = set(rk.split())
        cands = []
        for t in clubs:
            if t["id"] in seen or t["womens"] != womens:
                continue
            tk = normalize(t["name"])
            tt = set(tk.split())
            if ((crest_key(row.crest_url) and crest_key(row.crest_url) == crest_key(t["crestURL"]))
                    or (rt and tt and (rt <= tt or tt <= rt))
                    or difflib.SequenceMatcher(None, rk, tk).ratio() >= 0.85):
                cands.append(t)
        if len(cands) == 1:
            seen.add(cands[0]["id"])
            log(f"TEAMLIJST: '{row.name}' herkend als {cands[0]['id']}")
        else:
            missing.append(f"{row.name}{' (W)' if womens else ''} [{row.league_title}]")
    for m in missing:
        log(f"TEAMLIJST: in de game, geen ster op de bron (niet lootbaar): {m}")
    weg = {t["id"] for t in clubs if t["id"] not in seen}
    log(f"TEAMLIJST: {len(roster_rows)} clubs in de game, {len(seen)} herkend in de dataset, "
        f"{len(missing)} zonder ster, {len(weg)} niet op de teamlijst")
    return weg


ROSTER_MAX_DROP = 25


def drop_not_in_game(teams, weg: set[str]):
    """Haal clubs weg die niet op de officiële teamlijst staan. Boven
    ROSTER_MAX_DROP is eerder de koppeling of de pagina stuk dan dat EA zoveel
    clubs schrapte: dan niets weghalen en luid waarschuwen."""
    if len(weg) > ROSTER_MAX_DROP:
        log(f"TEAMLIJST WAARSCHUWING: {len(weg)} clubs niet herkend (> {ROSTER_MAX_DROP}); "
            "koppeling verdacht, niets weggehaald")
        return teams
    for t in teams:
        if t["id"] in weg:
            log(f"TEAMLIJST DROP: {t['id']} ({t['name']}, {t['starRating']}★) staat niet "
                "op de teamlijst van deze titel; klopt dat niet, koppel hem in aliases.json")
    return [t for t in teams if t["id"] not in weg]


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


def load_flags() -> dict:
    path = ROOT / "pipeline" / "flags.json"
    return json.loads(path.read_text(encoding="utf-8"))["flags"]


def load_national_teams(game: dict | None = None):
    """Landenteams komen uit een handmatige seed omdat fifauteam/fifagamenews
    ze als platte tekst tonen, zonder crest per team. Vlaggen (via
    pipeline/flags.json -> flagcdn.com) zijn wél altijd beschikbaar en geen
    EA/club-IP, dus die vullen crestURL i.p.v. de initialen-fallback.
    Elke titel heeft een eigen seed (games.json 'nationalTeams'): welke landen
    erin zitten verschilt per jaar."""
    rel = (game or {}).get("nationalTeams", "data/national-teams.json")
    if rel is None:
        log("NATIONAL: geen seed voor deze titel, geen landenteams opgenomen")
        return []
    path = ROOT / rel
    if not path.exists():
        log(f"NATIONAL: {rel} ontbreekt, geen landenteams opgenomen")
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    teams = doc["teams"]
    flags = load_flags()
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
        if not t["crestURL"]:
            code = t["countryCode"]
            flag = flags.get(code)
            if flag is None:
                raise SystemExit(
                    f"FOUT: geen vlag-mapping voor countryCode '{code}' ({t['id']}) "
                    "in pipeline/flags.json"
                )
            t["crestURL"] = f"https://flagcdn.com/{flag}.svg"
    log(f"NATIONAL: {len(teams)} landenteams uit seed, {sum(1 for t in teams if t['crestURL'])} met vlag-crest")
    return teams


def build(offline: bool, skip_colors: bool, skip_crest_check: bool,
          out_path: Path | None = None, game_id: str | None = None) -> None:
    game_id, game = resolve_game(game_id)
    out_path = out_path or ROOT / game["out"]
    # --out mag buiten de repo wijzen (tests, losse export), dus relative_to
    # is hier geen zekerheid.
    try:
        toon = out_path.relative_to(ROOT)
    except ValueError:
        toon = out_path
    log(f"GAME: {game_id} ({game['label']}) -> {toon}")
    stars_html, best_html = load_html(offline, game)
    star_rows = parse_stars(stars_html)
    league_rows = parse_best_teams(best_html)
    log(f"PARSE: {len(star_rows)} sterrenrijen, {len(league_rows)} league-rijen")

    league_meta = json.loads((ROOT / "pipeline" / "leagues.json").read_text(encoding="utf-8"))[
        "leagues"
    ]
    alias_doc = json.loads((ROOT / "pipeline" / "aliases.json").read_text(encoding="utf-8"))
    aliases = alias_doc["aliases"]
    aliases_teamlijst = alias_doc.get("teamlijst", {})

    star_rows = dedup_stars(star_rows)
    by_title = group_leagues(league_rows, league_meta)
    teams = join(star_rows, by_title, league_meta, aliases)
    try:
        roster_html = ((SNAPSHOTS / "leagues-clubs.html").read_text(encoding="utf-8")
                       if offline else fetch(game["leaguesClubsURL"]))
        weg = roster_check(teams, parse_roster(roster_html), aliases_teamlijst)
        if game.get("rosterDrop"):
            teams = drop_not_in_game(teams, weg)
    except Exception as e:  # noqa: BLE001
        # Een signaal naast de build, geen poortwachter.
        log(f"TEAMLIJST: check overgeslagen ({e})")
    upgrade_crests(teams, skip_crest_check)
    dominant_colors(teams, skip_colors)
    teams += load_national_teams(game)
    apply_overrides(teams, ROOT / game["overrides"])

    matched = sum(1 for t in teams if t["leagueId"])
    log(f"RESULTAAT: {len(teams)} teams, {matched} met league")

    from audit import run_audit
    run_audit(teams, log, game.get("auditMinStarLevels", 8))

    payload = {
        "schemaVersion": 1,
        "game": game["label"],
        # Waarschuwing voor de gebruiker; leeg zodra de bron echte data levert.
        # De webapp toont dit onder de titelkeuze, dus liegen we niet over hoe
        # hard deze set is.
        "note": game.get("note", ""),
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
            if title in by_title
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
    ap.add_argument("--game", help="titel-id uit games.json; standaard 'current'")
    ap.add_argument("--out", type=Path, help="overschrijf het uitvoerpad uit games.json")
    args = ap.parse_args()
    build(args.offline, args.skip_colors, args.skip_crest_check, args.out, args.game)
