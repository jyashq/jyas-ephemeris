"""Worked-example tests for earth orientation (Meeus ch. 12 and ch. 22).

References: Meeus, *Astronomical Algorithms*, 2nd ed. (1998).
- Example 12.b: 1987 April 10, 19h21m UT (JD 2446896.30625 by day
  arithmetic; T = -0.127296 as stated) -> mean GMST 8h34m57.0896s
  = 128.7378734 deg.
- Example 22.a: 1987 April 10, 0h TD (JD 2446895.5): mean obliquity
  23d 26m 27.407s, nutation -3.788s / +9.380s.
Nutation tolerances reflect the documented leading-terms truncation
(~0.1-0.2 arcsecond residual against the full IAU 1980 series). Engines
using the newer ERA-based Earth-rotation model (post-2000 publications)
differ from Meeus' 1998-era formula by ~0.2-0.3 seconds of time; that is a
model-generation difference, not an implementation error.
"""
from __future__ import annotations

import pytest

from jyas_ephemeris.earth import (
    apparent_sidereal_time_deg,
    mean_obliquity_deg,
    mean_sidereal_time_deg,
    nutation_deg,
    true_obliquity_deg,
)
from jyas_ephemeris.timecore import julian_day

JD_22A = 2446895.5


class TestSiderealTime:
    def test_meeus_12b_mean_gmst(self):
        # Meeus example 12.b: 1987 April 10, 19h21m UT -> theta0 = 128.7378734 deg.
        # (JD verified by day arithmetic: 2446896.30625; T = -0.127296 as stated.)
        jd = julian_day(1987, 4, 10, 19 + 21 / 60.0)
        assert jd == pytest.approx(2446896.30625, abs=1e-7)
        assert mean_sidereal_time_deg(jd) == pytest.approx(128.7378734, abs=1e-6)

    def test_sidereal_excess_per_solar_day(self):
        a = mean_sidereal_time_deg(julian_day(2000, 1, 1, 0.0))
        b = mean_sidereal_time_deg(julian_day(2000, 1, 2, 0.0))
        delta = (b - a) % 360.0
        # The sidereal excess over one mean solar day: ~3m56.56s of rotation.
        assert delta == pytest.approx(0.98564736629, abs=1e-6)

    def test_apparent_close_to_mean(self):
        # The equation of the equinoxes is bounded by about 1.2s of time,
        # i.e. ~18 arcsecond of sidereal angle.
        diff = abs(
            (apparent_sidereal_time_deg(JD_22A) - mean_sidereal_time_deg(JD_22A) + 180.0) % 360.0
            - 180.0
        )
        assert diff < 20.0 / 3600.0


class TestObliquity:
    def test_j2000_mean(self):
        # 23d 26m 21.448s.
        assert mean_obliquity_deg(2451545.0) == pytest.approx(23.439291111, abs=1e-6)

    def test_meeus_22a_mean(self):
        # Meeus example 22.a: eps0 = 23d 26m 27.407s on the 12.b instant.
        expected = 23 + 26 / 60.0 + 27.407 / 3600.0
        assert mean_obliquity_deg(JD_22A) == pytest.approx(expected, abs=1e-6)


class TestNutation:
    def test_meeus_22a_full_model(self):
        # Meeus example 22.a (1987 Apr 10, 0h TD): Delta psi = -3.788s.
        # For Delta eps the IAU 1980 evaluation (Explanatory Supplement
        # 1992 s.3.222, the series SOFA/ERFA tabulate) gives +9.44s at this
        # instant; the leading-terms sum in earth.py reproduces it within
        # the 0.01s truncation budget.
        dpsi, deps = nutation_deg(JD_22A)
        assert dpsi == pytest.approx(-3.788 / 3600.0, abs=0.01 / 3600.0)
        assert deps == pytest.approx(+9.440 / 3600.0, abs=0.01 / 3600.0)

    def test_true_obliquity_adds_delta(self):
        eps0 = mean_obliquity_deg(JD_22A)
        _, deps = nutation_deg(JD_22A)
        assert true_obliquity_deg(JD_22A) == pytest.approx(eps0 + deps, abs=1e-12)
