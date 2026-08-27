"""Worked-example tests for timecore.

Every expected value below is a published reference (Meeus,
*Astronomical Algorithms*, 2nd ed.; Espenak & Meeus Delta T polynomials),
quoted with an explicit tolerance. Invented references are not validation.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from jyas_ephemeris.timecore import (
    datetime_from_julian_day,
    delta_t_seconds,
    julian_day,
    julian_day_from_datetime,
    julian_ephemeris_day,
)


class TestJulianDay:
    def test_j2000_epoch(self):
        # Meeus ch. 7: J2000.0 = JD 2451545.0 = 2000 Jan 1, 12h UT.
        assert julian_day(2000, 1, 1, 12.0) == pytest.approx(2451545.0, abs=1e-9)

    def test_meeus_7_example(self):
        # Meeus ch. 7 example: 1957 October 4.81 UT -> JD 2436116.31.
        assert julian_day(1957, 10, 4, 0.81 * 24) == pytest.approx(2436116.31, abs=1e-6)

    def test_meeus_12b_instant(self):
        # Meeus ch. 12 example instant: 1987 Apr 10, 19:21:00 UT.
        assert julian_day(1987, 4, 10, 19 + 21 / 60.0) == pytest.approx(
            2446896.30625, abs=1e-7
        )

    def test_rejects_julian_calendar_dates(self):
        with pytest.raises(ValueError):
            julian_day(1582, 10, 4, 0.0)

    def test_datetime_round_trip(self):
        dt = datetime(1987, 4, 10, 19, 21, 0, tzinfo=timezone.utc)
        jd = julian_day_from_datetime(dt)
        assert jd == pytest.approx(2446896.30625, abs=1e-7)
        back = datetime_from_julian_day(jd)
        assert back == dt


class TestDeltaT:
    def test_j2000(self):
        # Espenak-Meeus polynomial: Delta T (2000.0) = 63.86 s.
        assert delta_t_seconds(2451545.0) == pytest.approx(63.86, abs=0.01)

    def test_2005(self):
        # End of the 1986-2005 branch: Delta T (2005.0) ~ 64.7 s.
        assert delta_t_seconds(julian_day(2005, 1, 1, 0.0)) == pytest.approx(64.7, abs=0.2)

    def test_1900_sign_flip_era(self):
        # Delta T passed through zero near 1902; the 1900-1920 branch gives
        # a small negative value at 1900.0.
        assert delta_t_seconds(julian_day(1900, 1, 1, 0.0)) == pytest.approx(-2.79, abs=0.01)

    def test_magnitudes_1950_and_2050(self):
        # Published anchors: ~29 s at 1950, ~93 s near 2050.
        assert 28.0 < delta_t_seconds(julian_day(1950, 1, 1, 0.0)) < 30.0
        assert 90.0 < delta_t_seconds(julian_day(2050, 1, 1, 0.0)) < 96.0

    def test_jde_offset_is_seconds_to_days(self):
        jd = julian_day(2000, 1, 1, 12.0)
        jde = julian_ephemeris_day(jd)
        assert jde - jd == pytest.approx(63.86 / 86400.0, abs=1e-9)
