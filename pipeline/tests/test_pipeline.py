"""Pipeline-tests tegen de gecommitte snapshots als fixtures."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from normalize import is_womens_name, match_name, normalize, strip_womens_marker  # noqa: E402
from parse import parse_best_teams, parse_stars  # noqa: E402

SNAP = ROOT / "pipeline" / "snapshots"


@pytest.fixture(scope="module")
def stars():
    return parse_stars((SNAP / "stars.html").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def leagues():
    return parse_best_teams((SNAP / "best-teams.html").read_text(encoding="utf-8"))


def test_normalize_strips_accents_punct_and_womens_marker():
    assert normalize("AS Saint-Étienne") == "as saint etienne"
    assert normalize("FC Barcelona (W)") == "fc barcelona"
    assert is_womens_name("Kansas City Current (W)")
    assert not is_womens_name("Arsenal")
    assert strip_womens_marker("FC Barcelona  (W)") == "FC Barcelona"


def test_match_prefers_exact_then_alias_then_unique_fuzzy():
    keys = ["arsenal", "arsenal tula", "real madrid"]
    assert match_name("arsenal", keys, {})[0] == "arsenal"
    assert match_name("gunners", keys, {"gunners": "arsenal"})[0] == "arsenal"
    assert match_name("real madryd", keys, {})[0] == "real madrid"
    assert match_name("totally unknown", keys, {})[0] is None


def test_stars_snapshot_shape(stars):
    assert len(stars) > 600
    psg = next(r for r in stars if r.rank == 1)
    assert psg.name == "Paris Saint-Germain" and psg.stars == 5.0
    assert all(0.5 <= r.stars <= 5.0 for r in stars)
    assert any(is_womens_name(r.name) for r in stars)


def test_best_teams_snapshot_shape(leagues):
    titles = {r.league_title for r in leagues}
    assert "PREMIER LEAGUE" in titles and len(titles) == 37
    pl = [r for r in leagues if r.league_title == "PREMIER LEAGUE"]
    assert len(pl) == 20
    assert any(r.name == "Arsenal" and r.squad_rating >= 80 for r in pl)
    assert all(1 <= r.squad_rating <= 99 for r in leagues)


def test_known_duplicate_leagues_are_copies(leagues):
    """De reden dat de drop-lijst bestaat; als de bron dit fixt, faalt deze
    test en kan de drop weg."""
    def roster(title):
        return sorted(normalize(r.name) for r in leagues if r.league_title == title)

    assert roster("A-LEAGUE") == roster("ÖSTERREICHISCHE BUNDESLIGA")
    assert roster("NWSL") == roster("WOMEN'S SUPER LEAGUE")


def test_overrides_applied_warned_and_flagged_obsolete(tmp_path, capsys):
    from build_teams import apply_overrides

    teams = [
        {"id": "eng.arsenal", "starRating": 5.0, "squadRating": 84},
        {"id": "ned.ajax", "starRating": 4.0, "squadRating": 77},
    ]
    ov = tmp_path / "overrides.json"
    ov.write_text(json.dumps({"overrides": [
        {"id": "ned.ajax", "starRating": 4.5, "reason": "in-game check"},
        {"id": "eng.arsenal", "starRating": 5.0},
        {"id": "weg.team", "starRating": 3.0},
    ]}), encoding="utf-8")
    apply_overrides(teams, ov)
    out = capsys.readouterr().out
    assert teams[1]["starRating"] == 4.5
    assert teams[1]["squadRating"] == 77, "squadRating zonder override blijft staan"
    assert teams[0]["starRating"] == 5.0
    assert "OVERRIDE OVERBODIG: eng.arsenal" in out
    assert "OVERRIDE WARN: 'weg.team'" in out


def test_full_build_offline(tmp_path):
    from build_teams import build

    out = tmp_path / "teams.json"
    build(offline=True, skip_colors=True, skip_crest_check=True, out_path=out)
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schemaVersion"] == 1
    teams = doc["teams"]
    ids = [t["id"] for t in teams]
    assert len(ids) == len(set(ids))
    clubs = [t for t in teams if t["kind"] == "club"]
    nationals = [t for t in teams if t["kind"] == "national"]
    assert len(clubs) > 600 and len(nationals) >= 20
    matched = [t for t in clubs if t["leagueId"]]
    assert len(matched) / len(clubs) > 0.85
    arsenal = next(t for t in clubs if t["id"] == "eng.arsenal")
    assert arsenal["starRating"] == 5.0 or arsenal["starRating"] >= 4.5
    assert arsenal["leagueId"] == "eng.1" and arsenal["squadRating"] >= 80
    assert arsenal["crestURL"].startswith("https://")
    whitelisted = {l["id"] for l in doc["leagues"] if l["defaultWhitelist"]}
    assert whitelisted == {"eng.1", "ger.1", "esp.1", "fra.1", "ita.1",
                           "ned.1", "por.1", "tur.1", "usa.1", "sau.1"}
    aut = [l for l in doc["leagues"] if l["id"] in ("aut.1", "eng.w1")]
    assert aut == [], "gedropte kopie-leagues horen niet in de output"
