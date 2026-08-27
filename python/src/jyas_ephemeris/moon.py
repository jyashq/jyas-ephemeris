"""The Moon: Meeus ch. 47 abridged ELP-2000/82, and the lunar nodes.

Theory: the abridged ELP-2000/82 tables of Meeus, *Astronomical
Algorithms*, 2nd ed., ch. 47 (Tables 47.A/47.B, 60 terms each, an
abridgment of Chapront-Touze & Chapront's ELP-2000/82). The coefficient
data is vendored mechanically by tools/prepare_meeus_moon.py (never
transcribed by hand) and its provenance lives beside the data.

Published accuracy of this abridgment is on the order of 10 arcseconds;
the measured bound against DE440s is recorded in tests/test_moon.py and
docs/REQUIREMENTS.md.

Node longitudes, mean equinox of date:
- mean node: the polynomial Meeus gives for Omega (ch. 47);
- true node: mean node plus Meeus's published five-term periodic
  correction (the same abridgment pymeeus implements), matching the
  "true"/osculating node to arcminute class — the accuracy class of the
  rest of this tier.

Apparent longitude adds nutation in longitude (IAU 1980, earth.py).
Parallax and the small lunar FK5 correction are below the tier's error
budget and are not applied; that is a documented scope choice.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .earth import nutation_deg

__all__ = [
    "geometric_ecliptic_deg",
    "apparent_moon",
    "mean_node_deg",
    "true_node_deg",
]

_DATA = Path(__file__).resolve().parent / "data" / "meeus_moon47.json"
_C_AU_PER_DAY = 173.1446326846693
_KM_PER_AU = 149597870.7

_cache: dict | None = None


def _table() -> dict:
    global _cache
    if _cache is None:
        with _DATA.open("r", encoding="ascii") as fh:
            _cache = json.load(fh)
    return _cache


def _args(jde_tt: float) -> dict[str, float]:
    """Fundamental arguments in degrees (Meeus eq. 47.1-47.6, 47.7-47.9)."""
    t = (jde_tt - 2451545.0) / 36525.0
    lp = (
        218.3164477
        + (481267.88123421 + (-0.0015786 + (1.0 / 538841.0 - t / 65194000.0) * t) * t) * t
    )
    d = (
        297.8501921
        + (445267.1114034 + (-0.0018819 + (1.0 / 545868.0 - t / 113065000.0) * t) * t) * t
    )
    m = 357.5291092 + (35999.0502909 + (-0.0001536 + t / 24490000.0) * t) * t
    mp = (
        134.9633964
        + (477198.8675055 + (0.0087414 + (1.0 / 69699.0 - t / 14712000.0) * t) * t) * t
    )
    f = (
        93.2720950
        + (483202.0175233 + (-0.0036539 + (-1.0 / 3526000.0 + t / 863310000.0) * t) * t) * t
    )
    a1 = 119.75 + 131.849 * t
    a2 = 53.09 + 479264.290 * t
    a3 = 313.45 + 481266.484 * t
    e = 1.0 + (-0.002516 - 0.0000074 * t) * t
    return {
        "t": t,
        "lp": lp, "d": d, "m": m, "mp": mp, "f": f,
        "a1": a1, "a2": a2, "a3": a3,
        "e": e, "e2": e * e,
    }


def geometric_ecliptic_deg(jde_tt: float) -> tuple[float, float, float]:
    """Geometric geocentric (longitude, latitude, distance-au) of the Moon.

    Longitude and latitude are referred to the MEAN equinox and ecliptic
    of date (VSOP87D-style frame); add nutation for apparent. ``jde_tt``
    is a Julian Ephemeris Day.
    """
    tab = _table()
    a = _args(jde_tt)
    rad = math.radians
    lr = tab["lr"]
    b = tab["b"]

    sigma_l = 0.0
    sigma_r = 0.0
    for (cd, cm, cmp_, cf, coeff_l, coeff_r) in lr:
        arg = cd * a["d"] + cm * a["m"] + cmp_ * a["mp"] + cf * a["f"]
        cl, cr = coeff_l, coeff_r
        am = abs(cm)
        if am == 1:
            cl *= a["e"]; cr *= a["e"]
        elif am == 2:
            cl *= a["e2"]; cr *= a["e2"]
        sigma_l += cl * math.sin(rad(arg))
        sigma_r += cr * math.cos(rad(arg))
    sigma_l += (
        3958.0 * math.sin(rad(a["a1"]))
        + 1962.0 * math.sin(rad(a["lp"] - a["f"]))
        + 318.0 * math.sin(rad(a["a2"]))
    )

    sigma_b = 0.0
    for (cd, cm, cmp_, cf, coeff_b) in b:
        arg = cd * a["d"] + cm * a["m"] + cmp_ * a["mp"] + cf * a["f"]
        cb = coeff_b
        am = abs(cm)
        if am == 1:
            cb *= a["e"]
        elif am == 2:
            cb *= a["e2"]
        sigma_b += cb * math.sin(rad(arg))
    sigma_b += (
        -2235.0 * math.sin(rad(a["lp"]))
        + 382.0 * math.sin(rad(a["a3"]))
        + 175.0 * math.sin(rad(a["a1"] - a["f"]))
        + 175.0 * math.sin(rad(a["a1"] + a["f"]))
        + 127.0 * math.sin(rad(a["lp"] - a["mp"]))
        - 115.0 * math.sin(rad(a["lp"] + a["mp"]))
    )

    lam = (a["lp"] + sigma_l / 1e6) % 360.0
    beta = sigma_b / 1e6
    delta_km = 385000.56 + sigma_r / 1e3
    return lam, beta, delta_km / _KM_PER_AU


def apparent_moon(jd_ut: float | None = None, jde_tt: float | None = None):
    """Apparent geocentric Moon as a dict (lambda apparent, beta, distance)."""
    from .timecore import julian_ephemeris_day

    if jde_tt is None:
        if jd_ut is None:
            raise ValueError("provide either jd_ut or jde_tt")
        jde_tt = julian_ephemeris_day(jd_ut)
    lam, beta, dist = geometric_ecliptic_deg(jde_tt)
    dpsi, _ = nutation_deg(jde_tt)
    lam_app = (lam + dpsi) % 360.0
    return {
        "body": "moon",
        "longitude_deg": lam_app,
        "latitude_deg": beta,
        "distance_au": dist,
        "light_time_days": dist / _C_AU_PER_DAY,
    }


def mean_node_deg(jde_tt: float) -> float:
    """Longitude of the Moon's mean ascending node, mean equinox of date."""
    t = (jde_tt - 2451545.0) / 36525.0
    omega = (
        125.0445479
        + (-1934.1362891 + (0.0020754 + (1.0 / 467441.0 - t / 60616000.0) * t) * t) * t
    )
    return omega % 360.0


def _spherical_and_rates_deg(jde_tt: float):
    """Geometric Moon position + analytic rates (Meeus series differentiated
    term-by-term). Returns (lam_deg, beta_deg, delta_au, lam_dot, beta_dot,
    delta_dot) with rates in deg/day and au/day."""
    tab = _table()
    t = (jde_tt - 2451545.0) / 36525.0
    a = _args(jde_tt)
    rad = math.radians

    # Rates of the fundamental arguments, deg/century (analytic derivatives).
    lp_r = (
        481267.88123421
        + (-2 * 0.0015786 + (3.0 / 538841.0 - 4.0 * t / 65194000.0) * t) * t
    )
    d_r = (
        445267.1114034
        + (-2 * 0.0018819 + (3.0 / 545868.0 - 4.0 * t / 113065000.0) * t) * t
    )
    m_r = 35999.0502909 + (-2 * 0.0001536 + 3.0 * t / 24490000.0) * t
    mp_r = (
        477198.8675055
        + (2 * 0.0087414 + (3.0 / 69699.0 - 4.0 * t / 14712000.0) * t) * t
    )
    f_r = (
        483202.0175233
        + (-2 * 0.0036539 + (-3.0 / 3526000.0 + 4.0 * t / 863310000.0) * t) * t
    )
    a1_r = 131.849
    a2_r = 479264.290

    # Eccentricity factor rate (deg^-1 per century factor handled inline).
    e = a["e"]
    de_dt = -0.002516 - 2 * 0.0000074 * t  # per century

    lr = tab["lr"]
    b = tab["b"]

    sigma_l = 0.0
    dsigma_l = 0.0
    sigma_r = 0.0
    dsigma_r = 0.0
    for (cd, cm, cmp_, cf, coeff_l, coeff_r) in lr:
        arg = cd * a["d"] + cm * a["m"] + cmp_ * a["mp"] + cf * a["f"]
        darg = cd * d_r + cm * m_r + cmp_ * mp_r + cf * f_r
        darg_rad = math.radians(darg)  # d/dT sin(rad(arg)) = cos(arg)*rad(darg/dT)
        cl, cr = coeff_l, coeff_r
        dcl, dcr = 0.0, 0.0
        am = abs(cm)
        if am == 1:
            cl *= e; cr *= e
            dcl = coeff_l * de_dt; dcr = coeff_r * de_dt
        elif am == 2:
            cl *= e * e; cr *= e * e
            dcl = coeff_l * 2 * e * de_dt; dcr = coeff_r * 2 * e * de_dt
        s_arg = math.sin(rad(arg))
        c_arg = math.cos(rad(arg))
        sigma_l += cl * s_arg
        dsigma_l += (dcl * s_arg + cl * darg_rad * c_arg)
        sigma_r += cr * c_arg
        dsigma_r += (dcr * c_arg - cr * darg_rad * s_arg)

    # Additive terms of sigma_l
    a1 = a["a1"]; af = a["lp"] - a["f"]; a2 = a["a2"]
    da1 = a1_r; daf = lp_r - f_r; da2 = a2_r
    sigma_l += 3958.0 * math.sin(rad(a1)) + 1962.0 * math.sin(rad(af)) + 318.0 * math.sin(rad(a2))
    dsigma_l += (
        3958.0 * math.radians(da1) * math.cos(rad(a1))
        + 1962.0 * math.radians(daf) * math.cos(rad(af))
        + 318.0 * math.radians(da2) * math.cos(rad(a2))
    )

    sigma_b = 0.0
    dsigma_b = 0.0
    for (cd, cm, cmp_, cf, coeff_b) in b:
        arg = cd * a["d"] + cm * a["m"] + cmp_ * a["mp"] + cf * a["f"]
        darg = cd * d_r + cm * m_r + cmp_ * mp_r + cf * f_r
        darg_rad = math.radians(darg)
        cb = coeff_b
        dcb = 0.0
        am = abs(cm)
        if am == 1:
            cb *= e
            dcb = coeff_b * de_dt
        elif am == 2:
            cb *= e * e
            dcb = coeff_b * 2 * e * de_dt
        s_arg = math.sin(rad(arg))
        sigma_b += cb * s_arg
        dsigma_b += (dcb * s_arg + cb * darg_rad * math.cos(rad(arg)))

    lp = a["lp"]; mp = a["mp"]
    # Additive terms of sigma_b
    sigma_b += (
        -2235.0 * math.sin(rad(lp))
        + 382.0 * math.sin(rad(a["a3"]))
        + 175.0 * math.sin(rad(a["a1"] - a["f"]))
        + 175.0 * math.sin(rad(a["a1"] + a["f"]))
        + 127.0 * math.sin(rad(lp - mp))
        - 115.0 * math.sin(rad(lp + mp))
    )
    dsigma_b += (
        -2235.0 * math.radians(lp_r) * math.cos(rad(lp))
        + 382.0 * math.radians(481266.484) * math.cos(rad(a["a3"]))
        + 175.0 * math.radians(a1_r - f_r) * math.cos(rad(a["a1"] - a["f"]))
        + 175.0 * math.radians(a1_r + f_r) * math.cos(rad(a["a1"] + a["f"]))
        + 127.0 * math.radians(lp_r - mp_r) * math.cos(rad(lp - mp))
        - 115.0 * math.radians(lp_r + mp_r) * math.cos(rad(lp + mp))
    )

    lam = (lp + sigma_l / 1e6) % 360.0
    beta = sigma_b / 1e6
    delta_km = 385000.56 + sigma_r / 1e3
    lam_dot = (lp_r + dsigma_l / 1e6) / 36525.0        # deg/day
    beta_dot = (dsigma_b / 1e6) / 36525.0              # deg/day
    delta_dot = (dsigma_r / 1e3) / 36525.0             # km/day
    return lam, beta, delta_km / _KM_PER_AU, lam_dot, beta_dot, delta_dot / _KM_PER_AU


def _osculating_node_deg(jde_tt: float) -> float:
    """Ascending node of the Moon's instantaneous orbital plane (rad of date).

    h = r x v from the position and its ANALYTIC series derivative (no
    numeric-differentiation noise); the node direction is z_hat x h.
    """
    lam, beta, delta, lam_dot, beta_dot, delta_dot = _spherical_and_rates_deg(jde_tt)
    lr, br, ld, bd, dd = (
        math.radians(lam),
        math.radians(beta),
        math.radians(lam_dot),
        math.radians(beta_dot),
        delta_dot,
    )
    cb, sb = math.cos(br), math.sin(br)
    r = (delta * cb * math.cos(lr), delta * cb * math.sin(lr), delta * sb)
    v = (
        dd * cb * math.cos(lr)
        - delta * bd * sb * math.cos(lr)
        - delta * ld * cb * math.sin(lr),
        dd * cb * math.sin(lr)
        - delta * bd * sb * math.sin(lr)
        + delta * ld * cb * math.cos(lr),
        dd * sb + delta * bd * cb,
    )
    h = (
        r[1] * v[2] - r[2] * v[1],
        r[2] * v[0] - r[0] * v[2],
        r[0] * v[1] - r[1] * v[0],
    )
    # Ascending-node direction: z_hat x h, pointing at the ascending node.
    nx = -h[1]
    ny = h[0]
    return math.degrees(math.atan2(ny, nx)) % 360.0


def true_node_deg(jde_tt: float, method: str = "osculating") -> float:
    """Longitude of the Moon's true ascending node, mean equinox of date.

    - method='osculating' (default): node of the Moon's instantaneous
      orbital plane from the position and its analytic derivative. This is
      the same quantity the incumbent engines call the true node.
    - method='abridged': mean node plus Meeus's published five-term
      periodic correction (arcminute-class).
    """
    if method == "osculating":
        return _osculating_node_deg(jde_tt)
    if method == "abridged":
        t = (jde_tt - 2451545.0) / 36525.0
        d = 297.8501921 + (445267.1114034 + (-0.0018819 + (1.0 / 545868.0 - t / 113065000.0) * t) * t) * t
        m = 357.5291092 + (35999.0502909 + (-0.0001536 + t / 24490000.0) * t) * t
        mp = 134.9633964 + (477198.8675055 + (0.0087414 + (1.0 / 69699.0 - t / 14712000.0) * t) * t) * t
        f = 93.2720950 + (483202.0175233 + (-0.0036539 + (-1.0 / 3526000.0 + t / 863310000.0) * t) * t) * t
        rad = math.radians
        corr = (
            -1.4979 * math.sin(rad(2.0 * (d - f)))
            - 0.15 * math.sin(rad(m))
            - 0.1226 * math.sin(rad(2.0 * d))
            + 0.1176 * math.sin(rad(2.0 * f))
            - 0.0801 * math.sin(rad(2.0 * (mp - f)))
        )
        return (mean_node_deg(jde_tt) + corr) % 360.0
    raise ValueError(f"unknown true-node method: {method!r}")
