"""Naam-normalisatie en fuzzy matching tussen de twee bronpagina's."""

from __future__ import annotations

import difflib
import re
import unicodedata

WOMENS_MARKER = re.compile(r"\(\s*w\s*\)", re.IGNORECASE)


def is_womens_name(name: str) -> bool:
    return bool(WOMENS_MARKER.search(name))


def strip_womens_marker(name: str) -> str:
    return re.sub(r"\s+", " ", WOMENS_MARKER.sub(" ", name)).strip()


def normalize(name: str) -> str:
    """Accenten, punctuatie en (W) weg, lowercase, whitespace samengevouwen."""
    n = WOMENS_MARKER.sub(" ", name)
    n = unicodedata.normalize("NFKD", n)
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.lower()
    n = re.sub(r"[^a-z0-9]+", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def slugify(name: str) -> str:
    return normalize(name).replace(" ", "-")


FUZZY_CUTOFF = 0.90


def match_name(
    star_key: str, league_keys: list[str], aliases: dict[str, str]
) -> tuple[str | None, str]:
    """Match een genormaliseerde sterrenpagina-naam tegen league-pagina-namen.

    Returns (league_key | None, methode). Fuzzy match alleen bij een unieke
    beste kandidaat boven de cutoff; bij twijfel liever unmatched dan gokken.
    """
    if star_key in league_keys:
        return star_key, "exact"
    if star_key in aliases:
        target = aliases[star_key]
        if target in league_keys:
            return target, "alias"
        return None, f"alias wijst naar onbekende naam '{target}'"
    candidates = difflib.get_close_matches(star_key, league_keys, n=2, cutoff=FUZZY_CUTOFF)
    if len(candidates) == 1:
        return candidates[0], "fuzzy"
    if len(candidates) > 1:
        r0 = difflib.SequenceMatcher(None, star_key, candidates[0]).ratio()
        r1 = difflib.SequenceMatcher(None, star_key, candidates[1]).ratio()
        if r0 - r1 > 0.04:
            return candidates[0], "fuzzy"
        return None, f"ambigu: {candidates}"
    return None, "geen kandidaat"
