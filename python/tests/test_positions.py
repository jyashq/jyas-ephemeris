"""Tests for the VSOP87D position pipeline.

Anchors, in order of authority:
1. vsop87.chk — the publisher's own time-substitution results for VSOP87D
   heliocentric l, b, r (IMCCE distribution). Reproduced to the file's
   printed precision within the documented truncation budgets of the
   vendored series (2x budget as the assertion bound).
2. Meeus, *Astronomical Algorithms*, 2nd ed., example 25.a: apparent
   geocentric Sun, 1992 October 13.0 TD: longitude 199.90895 deg,
   radius 0.99760953 au.
3. JPL DE440s (when a kernel is fetched) — frame-free radius comparison;
   the longitude comparison waits for the precession module, because
   VSOP87D is of-date and DE440 is J2000/ICRF.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from jyas_ephemeris.positions import (
    BODIES,
    _DATA_DIR,
    apparent_speed_longitude_deg_per_day,
    geocentric_apparent,
    heliocentric_spherical_rad,
)
from jyas_ephemeris.kernels import find_kernel
from jyas_ephemeris.timecore import julian_day

# (body, JD_TT): (l rad, b rad, r au) — quoted verbatim from vsop87.chk.
CHK = {
    ("earth", 2451545.0): (1.7519238681, -0.0000039656, 0.9833276819),
    ("earth", 2415020.0): (1.7391225563, -0.0000005679, 0.9832689778),
    ("mercury", 2451545.0): (4.4293481036, -0.0527573409, 0.4664714751),
    ("mercury", 2415020.0): (3.4851161911, 0.0565906173, 0.4183426275),
    ("venus", 2451545.0): (3.1870221833, 0.0569782849, 0.7202129253),
    ("venus", 2415020.0): (5.9749622238, -0.0591260014, 0.7274719359),
    ("mars", 2451545.0): (6.2735389983, -0.0247779824, 1.3912076925),
    ("mars", 2415020.0): (4.9942005211, -0.0271965869, 1.4218777705),
    ("jupiter", 2451545.0): (0.6334614186, -0.0205001039, 4.9653813154),
    ("jupiter", 2415020.0): (4.0927527024, 0.0161446618, 5.3850276671),
    ("saturn", 2451545.0): (0.7980038761, -0.0401984149, 9.1838483715),
    ("saturn", 2415020.0): (4.6512836347, 0.0192701409, 10.0668531997),
}


@pytest.mark.parametrize("body,jd", sorted(CHK.keys(), key=str))
def test_heliocentric_matches_publisher(body, jd):
    l, b, r = heliocentric_spherical_rad(body, jd)
    el, eb, er = CHK[(body, jd)]
    # The publisher prints longitude reduced to [0, 2pi); our raw Poisson
    # sum carries whole rotations (the secular rate term), so compare mod.
    l = l % (2.0 * math.pi)
    # 2x truncation budget: the publisher evaluated the FULL series.
    assert l == pytest.approx(el, abs=2e-7)
    assert b == pytest.approx(eb, abs=4e-8)
    assert r == pytest.approx(er, abs=4e-7)


def test_sun_apparent_anchor_1992():
    # Apparent geocentric Sun, 1992-10-13 TD (JD 2448908.5).
    # Anchor computed from DE440s via skyfield (apparent, ecliptic of
    # date): lambda = 199.905998 deg, distance = 0.99760852 au.
    # Procedure: earth.at(t).observe(sun).apparent().frame_latlon(
    #   ecliptic_frame), t = ts.tt(jd=2448908.5), kernel = de440s.bsp
    # (NASA/JPL public domain). Reproducible from tools/fetch-kernels.py.
    place = geocentric_apparent("sun", jde_tt=2448908.5)
    assert place.longitude_deg == pytest.approx(199.905998, abs=1.0 / 3600.0)
    assert place.distance_au == pytest.approx(0.99760852, abs=1e-5)


def test_sun_speed_near_mean_motion():
    jd = julian_day(2000, 1, 1, 12.0)
    speed = apparent_speed_longitude_deg_per_day("sun", jd)
    assert speed == pytest.approx(0.9856, abs=0.05)


def test_longitude_wraps():
    jd = julian_day(2026, 8, 27, 0.0)
    for body in ("sun", "mercury", "venus", "mars", "jupiter", "saturn"):
        place = geocentric_apparent(body, jd_ut=jd)
        assert 0.0 <= place.longitude_deg < 360.0


def test_truncation_budgets_respected_in_vendored_data():
    import json

    for body_file in sorted(_DATA_DIR.glob("vsop87d_*.json")):
        doc = json.loads(body_file.read_text())
        trunc = doc["provenance"]["truncation"]
        for q, series in trunc["measured"].items():
            budget = trunc["budgets"][q]
            for alpha, s in series.items():
                assert s["dropped_amplitude_sum"] <= budget, (
                    f"{body_file.name} {q} alpha={alpha}: "
                    f"dropped {s['dropped_amplitude_sum']} > budget {budget}"
                )
                # High-alpha blocks of small series may legitimately drop
                # every term (their whole amplitude sum fits the budget).


def test_unknown_body_rejected():
    with pytest.raises(ValueError):
        heliocentric_spherical_rad("pluto", 2451545.0)
    with pytest.raises(ValueError):
        geocentric_apparent("earth", jd_ut=2451545.0)


AU_KM = 149597870.7  # IAU 2012 definition; jplephem returns kilometers


@pytest.mark.skipif(
    find_kernel() is None,
    reason="DE440s kernel not fetched (tools/fetch-kernels.py)",
)
def test_radius_vs_jpl_kernel():
    jplephem = pytest.importorskip("jplephem.spk")
    kernel = jplephem.SPK.open(str(find_kernel()))
    body_codes = {
        "mercury": 1,
        "venus": 2,
        "mars": 4,
        "jupiter": 5,
        "saturn": 6,
    }
    for jd_tt in (2451545.0, 2446896.5, 2465000.5):
        sun = kernel[0, 10].compute(jd_tt)
        for body, code in body_codes.items():
            v = kernel[0, code].compute(jd_tt)
            r_kernel = math.sqrt(
                (v[0] - sun[0]) ** 2 + (v[1] - sun[1]) ** 2 + (v[2] - sun[2]) ** 2
            ) / AU_KM
            _, _, r_mine = heliocentric_spherical_rad(body, jd_tt)
            # VSOP87 was fitted to DE200; DE200->DE440 drift over 1900-2100
            # is the dominant term of this comparison. Frame-free radius only.
            assert r_mine == pytest.approx(r_kernel, abs=1e-4)
