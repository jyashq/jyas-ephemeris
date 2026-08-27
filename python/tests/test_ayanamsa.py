"""Tests for the ayanamsa tier.

Anchors and bounds:
- The six constant-anchored systems (lahiri, fagan_bradley, raman,
  krishnamurti, yukteshwar, ss_citra) are defined by published anchor
  constants (t0, a0) plus accumulated precession; their absolute values
  were swept against the incumbent engine's ayanamsa implementation over
  1900-2100 (worst 17.8 arcseconds, documented in REQUIREMENTS.md).
  In-repo assertions pin the structural properties: the ~50.29 arcsec/yr
  rate, J2000-anchored absolute values, and cross-system ordering.
- true_citra is star-computed (Simbad-astrometry Spica at exactly 180
  deg); measured bound vs the incumbent's star path: 1.8 arcseconds
  (fine 2026 scan), 0.55 arcseconds at the decade-sample worst.
"""
from __future__ import annotations

import pytest

from jyas_ephemeris.ayanamsa import SYSTEMS, ayanamsa_deg, sidereal_longitude_deg, spica_longitude_deg
from jyas_ephemeris.timecore import julian_day, julian_ephemeris_day

J2000 = 2451545.0


class TestRate:
    def test_precession_rate_lahiri(self):
        jde = julian_ephemeris_day(julian_day(2020, 1, 1, 0.0))
        a0 = ayanamsa_deg("lahiri", jde)
        a1 = ayanamsa_deg("lahiri", jde + 365.25)
        rate = (a1 - a0) * 3600.0
        # IAU 2006 general precession near J2000: ~50.29 arcsec/year.
        assert rate == pytest.approx(50.29, abs=0.10)

    def test_monotonic_increasing(self):
        jde = J2000
        vals = [ayanamsa_deg("lahiri", jde + i * 3652.5) for i in range(11)]
        assert all(b > a for a, b in zip(vals, vals[1:]))


class TestAnchors:
    def test_lahiri_j2000_value(self):
        # Anchor value of this implementation at J2000 (TT): 23.857056 deg,
        # consistent with the published Lahiri mean ayanamsa at J2000
        # (~23 deg 51.4 arcmin). Sweep bound vs the incumbent: <= 17.4
        # arcseconds over 1900-2100 (REQUIREMENTS.md).
        assert ayanamsa_deg("lahiri", J2000) == pytest.approx(23.857056, abs=0.01)

    def test_fagan_bradley_1950_value(self):
        # t0 = 2433282.42346 (1950.0), a0 = 24.042044444: ayanamsa AT t0 is
        # the anchor by construction.
        assert ayanamsa_deg("fagan_bradley", 2433282.42346) == pytest.approx(
            24.042044444, abs=0.01
        )

    def test_raman_j1900_value(self):
        assert ayanamsa_deg("raman", 2415020.0) == pytest.approx(21.01444, abs=0.01)

    def test_krishnamurti_j1900_value(self):
        assert ayanamsa_deg("krishnamurti", 2415020.0) == pytest.approx(22.363889, abs=0.01)

    def test_yukteshwar_j1900_value(self):
        assert ayanamsa_deg("yukteshwar", 2415020.0) == pytest.approx(21.082222, abs=0.01)

    def test_ss_citra_t0_value(self):
        assert ayanamsa_deg("ss_citra", 1903396.8128654) == pytest.approx(2.11070444, abs=0.01)


class TestTrueCitra:
    def test_star_computed_near_lahiri(self):
        # Both are Spica-at-180 constructions; they differ by < 1 deg over
        # the consumer range (measured vs incumbent: true_citra within
        # 1.8 arcsec of the incumbent's star path in the 2026 fine scan).
        for jde in (2451545.0, 2461041.5):
            d = abs(ayanamsa_deg("true_citra", jde) - ayanamsa_deg("lahiri", jde))
            assert d < 1.0

    def test_spica_longitude_j2000(self):
        # Spica's APPARENT ecliptic longitude at J2000 (true equinox of
        # date, precession + nutation, from the Simbad astrometry through
        # the IAU 2006 matrix): 203.837440 deg (mean-of-date value before
        # nutation is 203.841305).
        assert spica_longitude_deg(J2000) == pytest.approx(203.837440, abs=0.001)


class TestAPI:
    def test_unknown_system_rejected(self):
        with pytest.raises(ValueError):
            ayanamsa_deg("sidereal_tropical", J2000)

    def test_sidereal_conversion_wraps(self):
        lam = ayanamsa_deg("lahiri", J2000) + 5.0  # just above the ayanamsa
        assert sidereal_longitude_deg(lam, "lahiri", J2000) == pytest.approx(5.0, abs=1e-9)
        assert sidereal_longitude_deg(10.0, "lahiri", J2000) == pytest.approx(
            (10.0 - ayanamsa_deg("lahiri", J2000)) % 360.0, abs=1e-9
        )

    def test_all_seven_systems_present(self):
        assert set(SYSTEMS) == {
            "lahiri", "true_citra", "ss_citra", "fagan_bradley",
            "krishnamurti", "raman", "yukteshwar",
        }
