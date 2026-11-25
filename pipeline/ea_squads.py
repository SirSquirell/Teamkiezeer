"""Spelersratings per club van EA's eigen ratingsite.

Elke club staat op ratings?team=<eaId>, met de hele selectie in één keer in
__NEXT_DATA__ (ratingDetails.items, ook bij 30+ spelers). Gewone requests
volstaan; de site heeft geen bot-blokkade.
"""

from __future__ import annotations

import json
import re
import time

NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def parse_squad(html: str) -> list[list]:
    """[[spelerId, ovr, positie, [alternatieve posities]], ...], hoogste OVR eerst."""
    m = NEXT_DATA.search(html)
    if m is None:
        raise ValueError("EA-squad: geen __NEXT_DATA__, structuur veranderd?")
    details = json.loads(m.group(1))["props"]["pageProps"]["ratingDetails"]
    items = details.get("items") or []
    if details.get("totalItems", len(items)) > len(items):
        raise ValueError(f"EA-squad: {details['totalItems']} spelers, pagina toont er {len(items)}")
    out = []
    for it in items:
        alts = [a.get("shortLabel") for a in it.get("alternatePositions") or [] if a.get("shortLabel")]
        out.append([int(it["id"]), int(it["overallRating"]), it["position"]["shortLabel"], alts])
    out.sort(key=lambda p: (-p[1], p[0]))
    return out


def fetch_squads(base_url: str, team_ids, user_agent: str, log, delay: float = 0.3) -> dict:
    import requests

    session = requests.Session()
    session.headers["User-Agent"] = user_agent
    squads, failed = {}, []
    for n, tid in enumerate(team_ids, 1):
        for attempt in range(3):
            try:
                r = session.get(base_url, params={"team": tid}, timeout=60)
                r.raise_for_status()
                squads[str(tid)] = parse_squad(r.text)
                break
            except Exception as e:  # noqa: BLE001 - na 3 pogingen gelogd en overgeslagen
                if attempt == 2:
                    failed.append(tid)
                    log(f"squad {tid} mislukt: {e}")
                else:
                    time.sleep(2 * (attempt + 1))
        if n % 100 == 0:
            log(f"{n}/{len(team_ids)} squads")
        time.sleep(delay)
    return {"squads": squads, "failed": failed}
