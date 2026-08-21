"""Parsers voor de twee bronpagina's.

- fifagamenews FC 26 team star ratings: één tabel met rank / naam / sterren.
- fifauteam best teams: Elementor-tabs, per league een tab-titel en een tabel
  met squad rating / naam. Tab-titels en tabellen staan in documentvolgorde
  en matchen 1-op-1.
"""

from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass
class StarRow:
    rank: int
    name: str
    stars: float
    crest_url: str | None


@dataclass
class LeagueRow:
    league_title: str
    name: str
    squad_rating: int
    crest_url: str | None


def _crest_from_cell(cell) -> str | None:
    img = cell.find("img")
    if img is None:
        return None
    src = img.get("data-lazy-src") or img.get("src") or ""
    return src if src.startswith("http") else None


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
        name = " ".join(cells[1].get_text(" ", strip=True).split())
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
            name = " ".join(cells[1].get_text(" ", strip=True).split())
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
