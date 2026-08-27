"""Tests for houses, rise/set, and panchanga boundaries.

Static anchors were measured against the incumbent engine's outputs during
development (see REQUIREMENTS.md sweep bounds); the in-repo assertions pin
those values plus the structural laws of each module.
"""
from __future__ import annotations

import pytest

from jyas_ephemeris.timecore import julian_day
from jyas_ephemeris.houses import houses, houses_armc
from jyas_ephemeris.riseset import sun_rise_set, sun_transit, sun_altitude
from jyas_ephemeris.panchanga import (
    find_crossing,
    tithi_info,
    nakshatra_info,
    vimshottari_balance,
    VIMSHOTTARI_LORDS,
    VIMSHOTTARI_YEARS,
)


class TestHouses:
    def test_tropical_anchor_2000(self):
        # Anchor: Placidus, 2000-01-01 12h UT, lat 28.6 lon 77.2 east.
        # Measured against the incumbent houses implementation (< 0.02").
        out = houses(julian_day(2000, 1, 1, 12.0), 28.6, 77.2, "P")
        for cusp, expect in zip(out["cusps"], [
            100.176426, 122.806493, 147.740603, 177.446647, 212.090897,
            247.750406, 280.176426, 302.806493, 327.740603, 357.446647,
            32.090897, 67.750406,
        ]):
            assert cusp == pytest.approx(expect, abs=1.0 / 60.0)
        assert out["ascendant"] == pytest.approx(100.176426, abs=1.0 / 60.0)

    def test_sidereal_anchor_1992(self):
        # Sidereal Lahiri Placidus, 1992-04-12 00h UT, lat 23 lon 90 east.
        # Measured against the incumbent (< 16.7 arcseconds, the ayanamsa
        # layer's own bound).
        out = houses(julian_day(1992, 4, 12, 0.0), 23.0, 90.0, "P", "lahiri")
        for cusp, expect in zip(out["cusps"], [
            3.075637, 34.808067, 60.707641, 85.134168, 111.88202, 144.417734,
            183.075637, 214.808067, 240.707641, 265.134168, 291.88202,
            324.417734,
        ]):
            assert cusp == pytest.approx(expect, abs=1.0 / 60.0)

    def test_cusps_ascending(self):
        out = houses(julian_day(2026, 8, 27, 6.5), 28.6, 77.2, "P")
        c = out["cusps"]
        for i in range(12):
            gap = (c[(i + 1) % 12] - c[i]) % 360.0
            assert 0.0 < gap < 180.0, f"cusps not in order at {i}"

    def test_opposite_cusps(self):
        out = houses(julian_day(2026, 8, 27, 6.5), 23.0, 90.0, "P")
        c = out["cusps"]
        assert c[3] == pytest.approx((out["mc"] + 180.0) % 360.0, abs=1e-9)
        assert c[6] == pytest.approx((out["ascendant"] + 180.0) % 360.0, abs=1e-9)
        assert c[7] == pytest.approx((c[1] + 180.0) % 360.0, abs=1e-9)

    def test_polar_circle_refused(self):
        with pytest.raises(ValueError):
            houses_armc(100.0, 80.0, 24.0, "P")

    def test_whole_sign_starts_at_asc_sign(self):
        out = houses(julian_day(2026, 8, 27, 6.5), 23.0, 90.0, "W")
        assert all(abs(c - (out["cusps"][0] + i * 30)) % 360 < 1e-9 for i, c in enumerate(out["cusps"]))


class TestSunRiseSet:
    def test_delhi_rise_anchor(self):
        # 2026-08-27 Delhi (28.6139 N, 77.2090 E): measured vs the
        # incumbent rise routine within 10 s.
        r = sun_rise_set(julian_day(2026, 8, 27, 0.0), 28.6139, 77.2090)
        assert r["rise"] == pytest.approx(2461279.518348, abs=10.0 / 86400.0)
        assert r["set"] == pytest.approx(2461280.054639, abs=10.0 / 86400.0)
        assert r["polar"] is None

    def test_rise_between_start_and_set(self):
        r = sun_rise_set(julian_day(2026, 8, 27, 0.0), 28.6139, 77.2090)
        assert julian_day(2026, 8, 27, 0.0) < r["rise"] < r["set"] < r["rise"] + 1.2

    def test_altitude_at_rise_is_threshold(self):
        r = sun_rise_set(julian_day(2026, 8, 27, 0.0), 28.6139, 77.2090)
        assert sun_altitude(r["rise"], 28.6139, 77.2090) == pytest.approx(-0.8740, abs=0.01)

    def test_transit_after_start_and_high(self):
        t = sun_transit(julian_day(2026, 8, 27, 0.0), 28.6139, 77.2090)
        assert t > julian_day(2026, 8, 27, 0.0)
        assert sun_altitude(t, 28.6139, 77.2090) > 60.0


class TestPanchanga:
    def test_tithi_anchor_47a_instant(self):
        # 1992-04-12 0h TD: Moon 133.162655, Sun ~22.02 => diff ~111.14:
        # Shukla Dashami (index 10), ending when the difference reaches 120.
        info = tithi_info(2448724.5)
        assert info["index"] == 10
        assert info["paksha"] == "Shukla"
        assert info["name"] == "Dashami"
        assert info["end_jd_ut"] == pytest.approx(2448725.186865, abs=0.001)

    def test_tithi_sequence_spacing(self):
        # Successive tithi ends ~0.98-1.04 days apart (synodic rate).
        info = tithi_info(julian_day(2026, 8, 27, 0.0))
        e1 = info["end_jd_ut"]
        e2 = tithi_info(e1 + 0.01)["end_jd_ut"]
        assert 0.9 < (e2 - e1) < 1.1

    def test_nakshatra_index_and_lord(self):
        info = nakshatra_info(2448724.5)
        assert 1 <= info["index"] <= 27
        assert info["lord"] == VIMSHOTTARI_LORDS[(info["index"] - 1) % 9]

    def test_find_crossing_wraps(self):
        # A value that increases through the target must wrap-detect.
        seq = {"t": 0.0}
        def fn(jd):
            return (100.0 + (jd - seq["t"]) * 12.0) % 360.0
        root = find_crossing(fn, 120.0, 0.0, 10.0)
        assert fn(root) == pytest.approx(120.0, abs=1e-6)
        assert 1.0 < root < 2.0

    def test_find_crossing_no_crossing_raises(self):
        with pytest.raises(ValueError):
            find_crossing(lambda jd: 5.0, 120.0, 0.0, 10.0)

    def test_vimshottari_structure(self):
        v = vimshottari_balance(2451545.0)
        seq = v["mahadashas"]
        assert sum(VIMSHOTTARI_YEARS.values()) == 120
        # contiguous sequence, correct lord cycling
        for (l1, s1, e1), (l2, s2, e2) in zip(seq, seq[1:]):
            assert e1 == pytest.approx(s2, abs=1e-9)
            assert VIMSHOTTARI_LORDS[(VIMSHOTTARI_LORDS.index(l1) + 1) % 9] == l2
        total_days = seq[-1][2] - seq[0][1]
        assert total_days == pytest.approx(120.0 * 365.0, abs=1e-6)
        # balance arithmetic: remaining + elapsed == span of the running lord
        assert v["balance_remaining_days"] + v["balance_elapsed_days"] == pytest.approx(
            v["balance_span_days"], abs=1e-6
        )
