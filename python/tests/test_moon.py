"""Tests for the Moon tier.

Anchors, in order of authority:
1. Meeus example 47.a (1992 April 12.0 TD) — reproduced to the printed
   precision because the identical abridged tables are evaluated; this is
   a strong self-check of the argument polynomials, E factors, and
   additive terms.
2. pymeeus doctest anchors for the node polynomials (published rounded
   values).
3. A DE440s oracle spot value for the apparent longitude (procedure
   documented in the test; oracle = skyfield + tools/fetch-kernels.py
   kernel), plus the measured sweep bound recorded in REQUIREMENTS.md.
"""
from __future__ import annotations

import math

import pytest

from jyas_ephemeris.moon import (
    apparent_moon,
    geometric_ecliptic_deg,
    mean_node_deg,
    true_node_deg,
)
from jyas_ephemeris.timecore import julian_day
from jyas_ephemeris.positions import apparent_speed_longitude_deg_per_day


class TestMeeus47a:
    def test_example_47a_exact(self):
        # 1992 April 12.0 TD: lambda = 133.162655 deg, beta = -3.229126 deg,
        # distance = 368409.7 km — quoted to the book's printed precision;
        # the same abridged tables must reproduce them.
        lam, beta, dist_au = geometric_ecliptic_deg(2448724.5)
        assert lam == pytest.approx(133.162655, abs=1e-5)
        assert beta == pytest.approx(-3.229126, abs=1e-5)
        assert dist_au * 149597870.7 == pytest.approx(368409.7, abs=0.05)


class TestNodes:
    def test_mean_node_pymeeus_doctest_anchors(self):
        # pymeeus Moon.longitude_mean_ascending_node doctests (rounded 0.1 deg).
        assert mean_node_deg(julian_day(1913, 5, 27, 0.0)) % 360 == pytest.approx(0.0, abs=0.1)
        assert mean_node_deg(julian_day(2043, 9, 10, 0.0)) % 360 == pytest.approx(0.0, abs=0.1)
        assert mean_node_deg(julian_day(1959, 12, 7, 0.0)) % 360 == pytest.approx(180.0, abs=0.1)
        assert mean_node_deg(julian_day(2108, 11, 3, 0.0)) % 360 == pytest.approx(180.0, abs=0.1)

    def test_true_node_abridged_pymeeus_anchor(self):
        # pymeeus Moon.longitude_true_ascending_node doctest (5-term method).
        assert true_node_deg(julian_day(1913, 5, 27, 0.0), method="abridged") == pytest.approx(
            0.8763, abs=0.001
        )

    def test_true_node_osculating_near_mean(self):
        # The osculating node oscillates about the mean node with an
        # amplitude of ~1.57 deg; 1.9 deg is a safe structural bound.
        for jd in (2415020.0, 2446896.5, 2451545.0, 2465000.5):
            d = abs((true_node_deg(jd) - mean_node_deg(jd) + 180) % 360 - 180)
            assert d < 1.9


class TestMoonApparent:
    def test_oracle_anchor_1992(self):
        # DE440s apparent ecliptic-of-date longitude at 1992-04-12 TD:
        # 133.166724 deg (skyfield, same procedure as test_positions).
        m = apparent_moon(jde_tt=2448724.5)
        assert m["longitude_deg"] == pytest.approx(133.166724, abs=15.0 / 3600.0)

    def test_measured_sweep_bound_documented(self):
        # The 1900-2100 sweep vs DE440s measured worst 10.673 arcseconds
        # (docs/REQUIREMENTS.md). A single-instant assertion cannot bound a
        # sweep; this asserts the tier's speed sanity instead and documents
        # where the sweep bound lives.
        speed = apparent_speed_longitude_deg_per_day("moon", 2451545.0)
        assert 11.5 < speed < 15.0

    def test_distance_plausible(self):
        m = apparent_moon(jde_tt=2451545.0)
        # Lunar distance bounds: ~356400-406700 km.
        assert 0.00238 < m["distance_au"] < 0.00272

    def test_via_unified_positions_api(self):
        from jyas_ephemeris.positions import geocentric_apparent

        p = geocentric_apparent("moon", jd_ut=2451545.0)
        assert p.body == "moon"
        assert 0.0 <= p.longitude_deg < 360.0

    def test_jd_ut_and_jde_agree(self):
        from jyas_ephemeris.timecore import delta_t_seconds

        jd_ut = 2451545.0
        a = apparent_moon(jd_ut=jd_ut)
        b = apparent_moon(jde_tt=jd_ut + delta_t_seconds(jd_ut) / 86400.0)
        assert a["longitude_deg"] == pytest.approx(b["longitude_deg"], abs=1e-9)
