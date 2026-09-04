"""West-options wave: quadrant circle house systems + aspect enumeration.

Validation is by construction and invariant, not by invented printed
references: cusps must lie on their defining great circles (checked as
unit-vector plane membership), Porphyry must trisect the ecliptic
quadrants exactly, Morinus must return the RA circle points, and every
system must keep the quadrant/opposition structure.
"""
from __future__ import annotations

import math

import pytest

from jyas_ephemeris.aspects import ASPECTS, default_orbs, find_aspects, separation_deg
from jyas_ephemeris.houses import houses, houses_armc

# A mid-latitude northern instant: 2000-01-01 12:00 UT at 51.5N, 0W (London).
JD = 2451545.0
LAT = 51.5
LON = 0.0

SYSTEMS = ("P", "O", "R", "C", "M", "E", "W")


def _norm(vals):
    return [v % 360.0 for v in vals]


def test_regiomontanus_cusps_lie_on_defining_circles():
    out = houses_armc(_ramc(), LAT, 23.43678, system="R")
    eps = 23.43678
    north = (
        math.sin(math.radians(LAT)) * math.cos(math.radians(_ramc() + 180.0)),
        math.sin(math.radians(LAT)) * math.sin(math.radians(_ramc() + 180.0)),
        math.cos(math.radians(LAT)),
    )
    assert abs(math.sqrt(sum(c * c for c in north)) - 1.0) < 1e-12
    for k in (11, 12, 2, 3):
        d = math.radians((_ramc() + 30.0 * ((k + 2) % 12)) % 360.0)
        q = (math.cos(d), math.sin(d), 0.0)
        n = (
            north[1] * q[2] - north[2] * q[1],
            north[2] * q[0] - north[0] * q[2],
            north[0] * q[1] - north[1] * q[0],
        )
        lam = math.radians(out["cusps"][k - 1])
        v = (
            math.cos(lam),
            math.sin(lam) * math.cos(math.radians(eps)),
            math.sin(lam) * math.sin(math.radians(eps)),
        )
        assert abs(sum(n[i] * v[i] for i in range(3))) < 1e-7, f"cusp {k} off its circle"


def _ramc():
    from jyas_ephemeris.earth import apparent_sidereal_time_deg

    return (apparent_sidereal_time_deg(JD) + LON) % 360.0


def test_campanus_cusps_ordered_in_quadrants():
    out = houses_armc(_ramc(), LAT, 23.43678, system="C")
    c = _norm(out["cusps"])
    mc, asc = out["mc"] % 360.0, out["ascendant"] % 360.0
    assert (c[10] - mc) % 360.0 < (asc - mc) % 360.0
    assert (c[11] - c[10]) % 360.0 < (asc - c[10]) % 360.0


def test_porphyry_trisects_quadrants_exactly():
    out = houses_armc(_ramc(), LAT, 23.43678, system="O")
    c = out["cusps"]
    mc, asc = out["mc"], out["ascendant"]
    q_east = (asc - mc) % 360.0
    assert abs(((c[10] - mc) % 360.0) - q_east / 3.0) < 1e-9
    assert abs(((c[11] - mc) % 360.0) - 2.0 * q_east / 3.0) < 1e-9
    q_west = ((mc + 180.0) - asc) % 360.0
    assert abs(((c[1] - asc) % 360.0) - q_west / 3.0) < 1e-9


def test_morinus_cusps_carry_the_ra_circles():
    eps = 23.43678
    out = houses_armc(_ramc(), LAT, eps, system="M")
    for k in range(1, 13):
        ra_expected = math.radians((_ramc() + 30.0 * ((k + 2) % 12)) % 360.0)
        lam = math.radians(out["cusps"][k - 1])
        ra_from_lam = math.atan2(
            math.sin(lam) * math.cos(math.radians(eps)), math.cos(lam)
        )
        diff = abs((ra_from_lam - ra_expected + math.pi) % (2.0 * math.pi) - math.pi)
        assert diff < 1e-7, f"cusp {k} RA mismatch"


def test_morinus_house10_is_the_mc_point():
    out = houses_armc(_ramc(), LAT, 23.43678, system="M")
    d = (out["cusps"][9] - out["mc"]) % 360.0
    assert min(d, 360.0 - d) < 1e-7


@pytest.mark.parametrize("system", ["P", "O", "R", "C"])
def test_quadrant_systems_axis_structure(system):
    out = houses_armc(_ramc(), LAT, 23.43678, system=system)
    c = _norm(out["cusps"])
    # exact oppositions: 1/7, 2/8, 3/9, 4/10
    for a, b in ((0, 6), (1, 7), (2, 8), (3, 9)):
        assert abs(((c[b] - c[a]) % 360.0) - 180.0) < 1e-7


def test_houses_wrapper_new_systems_and_sidereal():
    out = houses(JD, LAT, LON, system="R")
    assert out["system"] == "R" and len(out["cusps"]) == 12
    out_s = houses(JD, LAT, LON, system="R", sidereal_system="lahiri")
    tropical = houses(JD, LAT, LON, system="R")
    from jyas_ephemeris.ayanamsa import ayanamsa_deg
    from jyas_ephemeris.timecore import julian_ephemeris_day

    ayan = ayanamsa_deg("lahiri", julian_ephemeris_day(JD))
    assert abs((out_s["ascendant"] - (tropical["ascendant"] - ayan)) % 360.0) < 1e-8


def test_separation_wraps_and_reduces():
    assert abs(separation_deg(350.0, 10.0) - 20.0) < 1e-12
    assert abs(separation_deg(10.0, 350.0) - 20.0) < 1e-12
    assert abs(separation_deg(0.0, 180.0) - 180.0) < 1e-12


def test_find_aspects_detects_trine_within_orb():
    orbs = default_orbs()
    got = find_aspects({"sun": 0.0, "mars": 119.5}, orbs=orbs)
    assert len(got) == 1
    row = got[0]
    assert row["name"] == "trine" and row["aspect_id"] == 3
    assert abs(row["deviation"] - (-0.5)) < 1e-9


def test_find_aspects_no_self_and_no_false_positive():
    assert find_aspects({"sun": 10.0}, orbs=default_orbs()) == []
    assert find_aspects({"sun": 0.0, "mars": 50.0}, orbs=default_orbs()) == []


def test_aspect_table_matches_sf_documented_ids():
    assert ASPECTS[1][0] == "conjunction" and ASPECTS[1][1] == 0.0
    assert ASPECTS[9] == ("quincunx", 150.0)
    assert ASPECTS[13][0] == "sesquiquintile"
