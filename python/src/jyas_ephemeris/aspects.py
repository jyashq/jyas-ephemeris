"""Aspect enumeration over ecliptic longitudes.

Angles and identifiers follow the aspect id table Solar Fire documents in
AspPat.ini (wave: solarfirereversed) so decoded corpora and jyas-side
callers can share one vocabulary; the table itself is common western
doctrine (major = Ptolemaic, minor incl. the quintile family).

Aspects are computed on TROPICAL longitudes as passed; sidereal callers
subtract their ayanamsa first, exactly as for house cusps.
"""
from __future__ import annotations

import math

__all__ = ["ASPECTS", "default_orbs", "find_aspects", "separation_deg"]

# id -> (name, angle); ids match the AspPat.ini table (0 = no aspect)
ASPECTS: dict[int, tuple[str, float]] = {
    1: ("conjunction", 0.0),
    2: ("opposition", 180.0),
    3: ("trine", 120.0),
    4: ("square", 90.0),
    5: ("sextile", 60.0),
    6: ("semisquare", 45.0),
    7: ("sesquisquare", 135.0),
    8: ("semisextile", 30.0),
    9: ("quincunx", 150.0),
    10: ("quintile", 72.0),
    11: ("biquintile", 144.0),
    12: ("semiquintile", 36.0),
    13: ("sesquiquintile", 108.0),
}

MAJOR_IDS = (1, 2, 3, 4, 5)


def default_orbs() -> dict[int, float]:
    """Conventional published-style orbs; callers override per tradition.

    Luminaries-gated and tradition-specific orbs belong to the caller's
    doctrine layer, not to this table.
    """
    return {
        1: 8.0, 2: 8.0, 3: 8.0, 4: 8.0, 5: 6.0,
        8: 2.0, 9: 2.0, 6: 2.0, 7: 2.0,
        10: 2.0, 11: 2.0, 12: 1.0, 13: 1.0,
    }


def separation_deg(lon_a: float, lon_b: float) -> float:
    """Angular separation in [0, 90] reduced the way aspects are read:
    the smaller of the direct and the complementary arc."""
    d = abs((lon_a - lon_b) % 360.0)
    return 360.0 - d if d > 180.0 else d


def find_aspects(
    longitudes: dict[str, float],
    orbs: dict[int, float] | None = None,
    aspect_ids: tuple[int, ...] = MAJOR_IDS,
) -> list[dict]:
    """All pairs of points within orb of any requested aspect.

    Returns dicts with keys body_a, body_b (a < b for determinism),
    aspect_id, name, angle, deviation (applied aspect minus exact angle,
    signed). No point aspects itself; each unordered pair appears at most
    once per aspect angle.
    """
    orbs = default_orbs() if orbs is None else orbs
    names = sorted(longitudes)
    out = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            sep = separation_deg(longitudes[a], longitudes[b])
            for aid in aspect_ids:
                name, angle = ASPECTS[aid]
                orb = orbs.get(aid)
                if orb is None:
                    continue
                dev = sep - angle
                if abs(dev) <= orb:
                    out.append({
                        "body_a": a,
                        "body_b": b,
                        "aspect_id": aid,
                        "name": name,
                        "angle": angle,
                        "deviation": round(dev, 10),
                    })
                    break
    out.sort(key=lambda r: (r["body_a"], r["body_b"], r["aspect_id"]))
    return out
