"""Parsers voor de twee bronpagina's.

- fifagamenews FC 26 team star ratings: één tabel met rank / naam / sterren.
- fifauteam best teams: Elementor-tabs, per league een tab-titel en een tabel
  met squad rating / naam. Tab-titels en tabellen staan in documentvolgorde
  en matchen 1-op-1.
- fifauteam leagues-clubs-national-teams: de officiële teamlijst van de titel,
  per league een toggle met een tabel van clubnamen. Bepaalt wat er echt in
  de game zit; sterren staan er niet op.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass
class StarRow:
    rank: int
    name: str
    stars: float
    crest_url: str | None


@dataclass
class RosterRow:
    league_title: str
    name: str
    crest_url: str | None


@dataclass
class LeagueRow:
    league_title: str
    name: str
    squad_rating: int
    crest_url: str | None


def _check_name(name: str, where: str) -> str:
    """Een teamnaam met < of > erin is nooit echt; zo'n rij faalt de build luid
    in plaats van via teams.json in de webapp te belanden. Een los teken aan de
    rand is wél echt gezien ("> St Mirren" op de sterrenpagina) en gaat eraf."""
    name = name.strip("<> ")
    if "<" in name or ">" in name:
        raise ValueError(f"{where}: teamnaam bevat HTML-tekens: {name!r}")
    return name


def _crest_from_cell(cell) -> str | None:
    img = cell.find("img")
    if img is None:
        return None
    src = img.get("data-lazy-src") or img.get("src") or ""
    return src if src.startswith("http") else None


def crest_key(url: str | None) -> str | None:
    """Bestandsnaam van een fifauteam-crest, zonder small/ en extensie. Beide
    bronnen linken dezelfde plaatjes, dus dit koppelt rijen waar de namen
    uiteenlopen ("Sporting" vs "Sporting CP")."""
    if not url:
        return None
    m = re.search(r"/teams/(?:small/)?([^/?#]+?)\.(?:webp|png|jpe?g)", url)
    # "Default" is het placeholder-plaatje voor clubs zonder logo, geen sleutel.
    if m is None or m.group(1).lower() == "default":
        return None
    return m.group(1).lower()


def parse_stars(html: str) -> list[StarRow]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        raise ValueError("sterrenpagina: geen tabel gevonden")
    rows: list[StarRow] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) != 3 or not cells[0].get_text(strip=True).isdigit():
            continue
        name = _check_name(" ".join(cells[1].get_text(" ", strip=True).split()), "sterrenpagina")
        stars = float(cells[2].get_text(strip=True).replace(",", "."))
        if not 0.5 <= stars <= 5.0:
            raise ValueError(f"sterrenpagina: onmogelijke sterwaarde {stars} voor {name}")
        rows.append(
            StarRow(
                rank=int(cells[0].get_text(strip=True)),
                name=name,
                stars=stars,
                crest_url=_crest_from_cell(cells[1]),
            )
        )
    if len(rows) < 400:
        raise ValueError(f"sterrenpagina: maar {len(rows)} rijen, structuur veranderd?")
    return rows


def parse_best_teams(html: str) -> list[LeagueRow]:
    soup = BeautifulSoup(html, "lxml")
    titles = [
        " ".join(div.get_text(" ", strip=True).split())
        for div in soup.select("div.elementor-tab-title")
    ]
    # Elementor rendert titels dubbel (desktop + mobile); ontdubbel op volgorde.
    seen: list[str] = []
    for t in titles:
        if t and (not seen or seen[-1] != t):
            seen.append(t)
    titles = list(dict.fromkeys(seen))
    tables = soup.find_all("table")
    if len(titles) != len(tables):
        raise ValueError(
            f"best-teams: {len(titles)} tab-titels maar {len(tables)} tabellen, structuur veranderd?"
        )
    rows: list[LeagueRow] = []
    for title, table in zip(titles, tables):
        count_before = len(rows)
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue
            rating_text = cells[0].get_text(strip=True)
            if not rating_text.isdigit():
                continue
            rating = int(rating_text)
            if not 1 <= rating <= 99:
                raise ValueError(f"best-teams: onmogelijke squad rating {rating} in {title}")
            name = _check_name(" ".join(cells[1].get_text(" ", strip=True).split()), "best-teams")
            rows.append(
                LeagueRow(
                    league_title=title,
                    name=name,
                    squad_rating=rating,
                    crest_url=_crest_from_cell(cells[1]),
                )
            )
        if len(rows) - count_before < 8:
            raise ValueError(f"best-teams: league '{title}' heeft verdacht weinig teams")
    return rows


# Toggles op de teamlijst die geen clubleague zijn: landenteams per
# continent en de "FC 26 VS FC 27"-samenvattingen.
ROSTER_SKIP = {"AFRICA", "ASIA", "EUROPE", "NORTH AMERICA", "OCEANIA", "SOUTH AMERICA",
               "FC 26 VS FC 27"}


def parse_roster(html: str) -> list[RosterRow]:
    soup = BeautifulSoup(html, "lxml")
    rows: list[RosterRow] = []
    for item in soup.select("div.elementor-toggle-item"):
        title_el = item.select_one(".elementor-toggle-title")
        table = item.select_one(".elementor-tab-content table")
        if title_el is None or table is None:
            continue
        for small in title_el.find_all("small"):
            small.extract()
        title = " ".join(title_el.get_text(" ", strip=True).split())
        if title in ROSTER_SKIP:
            continue
        for td in table.find_all("td"):
            img = td.find("img")
            src = (img.get("data-lazy-src") or img.get("src")) if img else None
            # De links in een cel zijn markeringen (Promoted, New Team, …).
            for a in td.find_all("a"):
                a.extract()
            name = " ".join(td.get_text(" ", strip=True).split())
            if not name or name.endswith(":") or name == "Rest of World":
                continue
            rows.append(RosterRow(league_title=title, name=_check_name(name, "teamlijst"),
                                  crest_url=src))
    if len(rows) < 400:
        raise ValueError(f"teamlijst: maar {len(rows)} clubs, structuur veranderd?")
    return rows
