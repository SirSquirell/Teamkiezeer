"""Tests voor de EA-selecties, het team-OVR-model en de vormgeschiedenis."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from ea_form import update_form  # noqa: E402
from ea_squads import parse_squad  # noqa: E402
from team_rating import FORMATIONS, best_xi, rate  # noqa: E402


def squad(gk=80, d=80, m=80, a=80, extra=()):
    s = [[1, gk, "GK", []]]
    s += [[10 + i, d, p, []] for i, p in enumerate(("LB", "CB", "CB", "RB"))]
    s += [[20 + i, m, p, []] for i, p in enumerate(("CDM", "CM", "CM", "CAM"))]
    s += [[30 + i, a, p, []] for i, p in enumerate(("LW", "ST", "RW", "ST"))]
    return s + list(extra)


def test_parse_squad_reads_next_data_sorted_by_ovr():
    items = [
        {"id": 5, "overallRating": 70, "position": {"shortLabel": "CB"}, "alternatePositions": []},
        {"id": 6, "overallRating": 88, "position": {"shortLabel": "ST"},
         "alternatePositions": [{"shortLabel": "LW"}]},
    ]
    data = {"props": {"pageProps": {"ratingDetails": {"items": items, "totalItems": 2}}}}
    html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'
    assert parse_squad(html) == [[6, 88, "ST", ["LW"]], [5, 70, "CB", []]]


def test_parse_squad_refuses_truncated_page():
    data = {"props": {"pageProps": {"ratingDetails": {"items": [], "totalItems": 30}}}}
    html = f'<script id="__NEXT_DATA__">{json.dumps(data)}</script>'
    try:
        parse_squad(html)
    except ValueError:
        return
    raise AssertionError("afgekapte selectie had moeten falen")


def test_best_xi_fills_every_slot_once():
    for formation in FORMATIONS.values():
        xi = best_xi(squad(), formation)
        assert sorted(s for s, _ in xi) == sorted(formation)


def test_rate_flat_squad_is_its_own_rating():
    weights = {"gk": 0.1, "def": 0.3, "mid": 0.3, "att": 0.3, "const": 0.0}
    assert abs(rate(squad(), weights)["ovr"] - 80) < 1e-9


def test_better_striker_raises_rating():
    base = rate(squad())["ovr"]
    star = rate(squad(extra=[[99, 92, "ST", []]]))["ovr"]
    assert star > base


def test_update_form_only_grows_history_on_change():
    first = update_form(None, {"1": 80.0, "2": 70.0}, "2026-11-14")
    assert first["baseline"] == "2026-11-14" and len(first["history"]) == 1
    assert first["form"]["1"] == {"ovr": 80.0, "delta": 0.0, "sinceBaseline": 0.0}

    same = update_form(first, {"1": 80.0, "2": 70.0}, "2026-11-21")
    assert len(same["history"]) == 1 and same["checked"] == "2026-11-21"

    moved = update_form(same, {"1": 81.2, "2": 69.5}, "2026-11-28")
    assert len(moved["history"]) == 2
    assert moved["form"]["1"]["delta"] == 1.2
    assert moved["form"]["2"]["delta"] == -0.5

    again = update_form(moved, {"1": 81.7, "2": 69.5}, "2026-12-05")
    assert again["form"]["1"] == {"ovr": 81.7, "delta": 0.5, "sinceBaseline": 1.7}
