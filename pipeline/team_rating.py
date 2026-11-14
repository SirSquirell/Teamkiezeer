"""Team-OVR uit spelersratings: beste elftal over een paar gangbare formaties,
dan lijngemiddelden en een gewogen totaal.

Het gewicht per lijn is gefit op de clubs in stars-fc27.json met basis
ovr-gemeten (echte team-OVR uit de gamedatabase); zie docs/data-audit-fc27.md.
"""

from __future__ import annotations

LINE = {
    "GK": "gk",
    "CB": "def", "LB": "def", "RB": "def", "LWB": "def", "RWB": "def",
    "CDM": "mid", "CM": "mid", "CAM": "mid", "LM": "mid", "RM": "mid",
    "ST": "att", "CF": "att", "LW": "att", "RW": "att",
}

# Per slot de posities die er passen; de eerste is de echte.
SLOTS = {
    "GK": ("GK",),
    "CB": ("CB",),
    "LB": ("LB", "LWB"),
    "RB": ("RB", "RWB"),
    "CDM": ("CDM", "CM"),
    "CM": ("CM", "CDM", "CAM"),
    "CAM": ("CAM", "CM", "CF"),
    "LM": ("LM", "LW"),
    "RM": ("RM", "RW"),
    "LW": ("LW", "LM"),
    "RW": ("RW", "RM"),
    "ST": ("ST", "CF"),
}

FORMATIONS = {
    "4-3-3": ("GK", "LB", "CB", "CB", "RB", "CDM", "CM", "CM", "LW", "ST", "RW"),
    "4-4-2": ("GK", "LB", "CB", "CB", "RB", "LM", "CM", "CM", "RM", "ST", "ST"),
    "4-2-3-1": ("GK", "LB", "CB", "CB", "RB", "CDM", "CDM", "LM", "CAM", "RM", "ST"),
    "4-1-2-1-2": ("GK", "LB", "CB", "CB", "RB", "CDM", "CM", "CM", "CAM", "ST", "ST"),
    "3-5-2": ("GK", "CB", "CB", "CB", "LM", "CDM", "CDM", "RM", "CAM", "ST", "ST"),
}

# Een speler buiten zijn posities verliest in de game flink; zonder exacte
# per-positie-OVR rekenen we een vaste straf.
OUT_OF_POSITION = 8
ALT_POSITION = 1

# Kleinste-kwadratenfit op 266 clubs met gemeten FC 27-team-OVR, EA-selecties
# van 2026-11-14: 5-voudig gekruist 0,53 OVR gemiddeld ernaast, 84% exact
# dezelfde ster. Andere gewichten = andere absolute OVR's: bump dan MODEL in
# ea_form.py, anders leest de wijziging als vorm.
WEIGHTS = {"gk": 0.08, "def": 0.3927, "mid": 0.3428, "att": 0.1523, "const": 1.275}


def best_xi(squad, formation):
    """Gretig: sterkste speler eerst naar de beste vrije slot. squad is
    [[id, ovr, pos, [alts]], ...]. Geeft [(slot, ovr_in_slot), ...]."""
    open_slots = list(formation)
    xi = []
    for _pid, ovr, pos, alts in sorted(squad, key=lambda p: -p[1]):
        if not open_slots:
            break
        best = None
        for i, slot in enumerate(open_slots):
            fits = SLOTS[slot]
            if pos == fits[0]:
                cand = ovr
            elif pos in fits:
                cand = ovr - ALT_POSITION
            elif any(a in fits for a in alts):
                cand = ovr - ALT_POSITION
            else:
                continue
            if best is None or cand > best[1]:
                best = (i, cand)
        if best is not None:
            xi.append((open_slots.pop(best[0]), best[1]))
    # Lege slots (te weinig spelers op die plek): beste overgebleven speler, met straf.
    used = len(xi)
    rest = sorted((p[1] for p in squad), reverse=True)[used:]
    for slot in open_slots:
        xi.append((slot, (rest.pop(0) if rest else 40) - OUT_OF_POSITION))
    return xi


def lines(xi):
    out = {}
    for line in ("gk", "def", "mid", "att"):
        vals = [v for slot, v in xi if LINE[slot] == line]
        out[line] = sum(vals) / len(vals)
    return out


def rate(squad, weights=None):
    """Hoogste team-OVR over de formaties. Geeft dict met ovr (float),
    lijnen en formatie."""
    w = weights or WEIGHTS
    best = None
    for name, formation in FORMATIONS.items():
        ln = lines(best_xi(squad, formation))
        ovr = sum(w[k] * ln[k] for k in ("gk", "def", "mid", "att")) + w["const"]
        if best is None or ovr > best["ovr"]:
            best = {"ovr": ovr, "formation": name, **ln}
    return best
