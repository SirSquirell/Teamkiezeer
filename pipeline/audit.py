"""Automatische audit op de gebouwde dataset.

Twee niveaus:
- HARD: structurele invarianten; falen breekt de build (liever geen data
  dan stille rommel).
- WARN: ankerverwachtingen die over het seizoen kunnen schuiven; worden
  gelogd zodat drift opvalt in de Action-output zonder de build te breken.
"""

from __future__ import annotations

from collections import Counter

# Ankers: (team-id, verwachte sterren nu, harde ondergrens).
# De ondergrens vangt parse-fouten (kolommen verwisseld, komma's kapot);
# de verwachting vangt seizoensdrift op die een mens even moet bekijken.
ANCHORS = [
    ("fra.paris-saint-germain", 5.0, 4.0),
    ("esp.real-madrid", 5.0, 4.0),
    ("esp.fc-barcelona", 5.0, 4.0),
    ("eng.arsenal", 5.0, 4.0),
    ("eng.liverpool", 5.0, 4.0),
    ("ger.bayern", 5.0, 4.0),
    ("ned.ajax", 4.0, 3.0),
    ("ned.psv", 4.0, 3.0),
]


def run_audit(teams: list[dict], log) -> None:
    clubs = [t for t in teams if t["kind"] == "club"]
    matched = [t for t in clubs if t["leagueId"]]

    def hard(cond: bool, msg: str) -> None:
        if not cond:
            raise SystemExit(f"AUDIT HARD FAIL: {msg}")

    hard(550 <= len(clubs) <= 800, f"clubaantal {len(clubs)} buiten 550..800")
    hard(len(matched) / len(clubs) > 0.85, "minder dan 85% clubs met league")

    stars = Counter(t["starRating"] for t in clubs)
    hard(len(stars) >= 8, f"maar {len(stars)} sterrenniveaus, verwacht >=8")
    hard(all(s * 2 == int(s * 2) and 0.5 <= s <= 5.0 for s in stars), "ster buiten 0.5-stappen")
    hard(3 <= stars.get(5.0, 0) <= 30, f"{stars.get(5.0, 0)} teams op 5.0 sterren, verwacht 3..30")

    for t in matched:
        hard(40 <= t["squadRating"] <= 99, f"squad rating {t['squadRating']} bij {t['id']}")

    by_league = Counter(t["leagueId"] for t in matched)
    for league, count in by_league.items():
        hard(count >= 8, f"league {league} heeft maar {count} teams")

    by_id = {t["id"]: t for t in teams}
    for team_id, expected, floor in ANCHORS:
        team = by_id.get(team_id)
        if team is None:
            log(f"AUDIT WARN: anker {team_id} niet in dataset")
            continue
        hard(team["starRating"] >= floor, f"anker {team_id} op {team['starRating']}★ (< {floor})")
        if team["starRating"] != expected:
            log(
                f"AUDIT WARN: {team_id} is {team['starRating']}★, anker verwachtte {expected}★ "
                "— seizoensdrift? Werk pipeline/audit.py bij na een spot-check."
            )

    # Kruisconsistentie tussen de twee onafhankelijke bronnen: sterren
    # (fifagamenews) horen monotoon te lopen met squad rating (fifauteam).
    # Een team dat ver van zijn bucket-gemiddelde ligt is verdacht.
    means: dict[float, float] = {}
    for level in sorted({t["starRating"] for t in matched}):
        bucket = [t["squadRating"] for t in matched if t["starRating"] == level]
        means[level] = sum(bucket) / len(bucket)
    levels = sorted(means)
    for lo, hi in zip(levels, levels[1:]):
        hard(means[hi] > means[lo] - 1,
             f"bucket {hi}★ (gem. {means[hi]:.1f}) lager dan {lo}★ ({means[lo]:.1f})")
    outliers = [
        (t["id"], t["starRating"], t["squadRating"], means[t["starRating"]])
        for t in matched
        if abs(t["squadRating"] - means[t["starRating"]]) > 6
    ]
    for team_id, star, rating, mean in outliers:
        log(f"AUDIT WARN: {team_id} heeft {rating} OVR op {star}★ "
            f"(bucketgemiddelde {mean:.1f}) — bron-inconsistentie?")

    nationals = [t for t in teams if t["kind"] == "national"]
    for t in nationals:
        hard(0.5 <= t["starRating"] <= 5.0 and 40 <= t["squadRating"] <= 99,
             f"national {t['id']} buiten bereik")
        hard(bool(t["crestURL"]), f"national {t['id']} heeft geen crestURL")

    log(f"AUDIT: OK — {len(clubs)} clubs, {len(nationals)} landen, "
        f"sterrenverdeling {dict(sorted(stars.items(), reverse=True))}")
