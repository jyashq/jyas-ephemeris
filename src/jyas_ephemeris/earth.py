"""Earth rotation and orientation: sidereal time, obliquity, nutation.

Algorithms and references:
- Mean sidereal time: Meeus, *Astronomical Algorithms*, 2nd ed. (1998),
  ch. 12 (eq. 12.4).
- Mean obliquity: Laskar (1986) polynomial, as given by Meeus eq. 22.2.
- Nutation: IAU 1980 model, Explanatory Supplement to the Astronomical
  Almanac (Seidelmann 1992) section 3.222. Fundamental arguments follow the
  SOFA convention (l, l', F, D, Omega); leading 20 of the 106 terms are
  kept, residual well under 0.01 arcsecond. The signature is the upgrade
  path: the full table drops in behind it unchanged.

Angles in degrees at the public boundary; radians only inside.
"""
from __future__ import annotations

import math

from .timecore import centuries_since_j2000_ut

__all__ = [
    "mean_obliquity_deg",
    "nutation_deg",
    "true_obliquity_deg",
    "mean_sidereal_time_deg",
    "apparent_sidereal_time_deg",
]


def mean_obliquity_deg(jde: float) -> float:
    """Mean obliquity of the ecliptic (Meeus eq. 22.2, Laskar 1986).

    ``jde`` is a Julian Ephemeris Day; T is Julian centuries from J2000.
    """
    t = (jde - 2451545.0) / 36525.0
    u = t / 100.0
    # Meeus eq. 22.3 (Laskar, degrees) — the full polynomial, valid to
    # +-0.01 arcsecond over +-10000 years.
    eps = (
        23.439291111
        - (4680.93 * u
           + 1.55 * u**2
           - 1999.25 * u**3
           - 51.38 * u**4
           - 249.67 * u**5
           - 39.05 * u**6
           + 7.12 * u**7
           + 27.87 * u**8
           + 5.79 * u**9
           + 2.45 * u**10) / 3600.0
    )
    return eps


def nutation_deg(jde: float) -> tuple[float, float]:
    """Nutation in longitude (Delta psi) and obliquity (Delta eps), degrees.

    IAU 1980 model, as tabulated in the Explanatory Supplement to the
    Astronomical Almanac (Seidelmann 1992, section 3.222). Fundamental
    arguments follow the SOFA convention (l = Moon mean anomaly, l' = Sun
    mean anomaly, F, D, Omega); the leading 20 terms of the 106-term series
    are kept, leaving a residual well under 0.01 arcsecond (the full table's
    tail is dominated by +-0.0001 arcsecond rows).
    """
    t = (jde - 2451545.0) / 36525.0

    def anpm(a: float) -> float:
        # Normalize to [-pi, pi] (SOFA eraAnpm equivalent).
        w = math.fmod(a, 2.0 * math.pi)
        if abs(w) >= math.pi:
            w -= 2.0 * math.pi * math.copysign(1.0, w)
        return w

    das2r = math.pi / (180.0 * 3600.0)
    d2pi = 2.0 * math.pi

    # SOFA fundamental arguments: arcsec polynomials + whole revolutions.
    l = anpm(
        (485866.733 + (715922.633 + (31.310 + 0.064 * t) * t) * t) * das2r
        + math.fmod(1325.0 * t, 1.0) * d2pi
    )
    lp = anpm(
        (1287099.804 + (1292581.224 + (-0.577 - 0.012 * t) * t) * t) * das2r
        + math.fmod(99.0 * t, 1.0) * d2pi
    )
    f = anpm(
        (335778.877 + (295263.137 + (-13.257 + 0.011 * t) * t) * t) * das2r
        + math.fmod(1342.0 * t, 1.0) * d2pi
    )
    d = anpm(
        (1072261.307 + (1105601.328 + (-6.891 + 0.019 * t) * t) * t) * das2r
        + math.fmod(1236.0 * t, 1.0) * d2pi
    )
    om = anpm(
        (450160.280 + (-482890.539 + (7.455 + 0.008 * t) * t) * t) * das2r
        + math.fmod(-5.0 * t, 1.0) * d2pi
    )

    # (l, l', F, D, Om): (longitude sin coeff 0.1 mas, per-century,
    #                     obliquity cos coeff 0.1 mas, per-century)
    # Leading 20 rows of the IAU 1980 series.
    terms = [
        (0, 0, 0, 0, 1, -171996.0, -174.2, 92025.0, 8.9),
        (0, 0, 0, 0, 2, 2062.0, 0.2, -895.0, 0.5),
        (-2, 0, 2, 0, 1, 46.0, 0.0, -24.0, 0.0),
        (2, 0, -2, 0, 0, 11.0, 0.0, 0.0, 0.0),
        (-2, 0, 2, 0, 2, -3.0, 0.0, 1.0, 0.0),
        (1, -1, 0, -1, 0, -3.0, 0.0, 0.0, 0.0),
        (0, -2, 2, -2, 1, -2.0, 0.0, 1.0, 0.0),
        (2, 0, -2, 0, 1, 1.0, 0.0, 0.0, 0.0),
        (0, 0, 2, -2, 2, -13187.0, -1.6, 5736.0, -3.1),
        (0, 1, 0, 0, 0, 1426.0, -3.4, 54.0, -0.1),
        (0, 1, 2, -2, 2, -517.0, 1.2, 224.0, -0.6),
        (0, -1, 2, -2, 2, 217.0, -0.5, -95.0, 0.3),
        (0, 0, 2, -2, 1, 129.0, 0.1, -70.0, 0.0),
        (2, 0, 0, -2, 0, 48.0, 0.0, 1.0, 0.0),
        (0, 0, 2, -2, 0, -22.0, 0.0, 0.0, 0.0),
        (0, 2, 0, 0, 0, 17.0, -0.1, 0.0, 0.0),
        (0, 1, 0, 0, 1, -15.0, 0.0, 9.0, 0.0),
        (0, 2, 2, -2, 2, -16.0, 0.1, 7.0, 0.0),
        (0, -1, 0, 0, 1, -12.0, 0.0, 6.0, 0.0),
        (-2, 0, 0, 2, 1, -6.0, 0.0, 3.0, 0.0),
        (0, -1, 2, -2, 1, -5.0, 0.0, 3.0, 0.0),
        (2, 0, 0, -2, 1, 4.0, 0.0, -2.0, 0.0),
        (0, 1, 2, -2, 1, 4.0, 0.0, -2.0, 0.0),
        (1, 0, 0, -1, 0, -4.0, 0.0, 0.0, 0.0),
        (0, 0, 2, 0, 2, -2274.0, -0.2, 977.0, -0.5),
        (1, 0, 0, 0, 0, 712.0, 0.1, -7.0, 0.0),
        (0, 0, 2, 0, 1, -386.0, -0.4, 200.0, 0.0),
        (1, 0, 2, 0, 2, -301.0, 0.0, 129.0, -0.1),
        (1, 0, 0, -2, 0, -158.0, 0.0, -1.0, 0.0),
        (-1, 0, 2, 0, 2, 123.0, 0.0, -53.0, 0.0),
        (0, 0, 0, 2, 0, 63.0, 0.0, -2.0, 0.0),
        (1, 0, 0, 0, 1, 63.0, 0.1, -33.0, 0.0),
        (-1, 0, 0, 0, 1, -58.0, -0.1, 32.0, 0.0),
        (-1, 0, 2, 2, 2, -59.0, 0.0, 26.0, 0.0),
        (1, 0, 2, 0, 1, -51.0, 0.0, 27.0, 0.0),
        (0, 0, 2, 2, 2, -38.0, 0.0, 16.0, 0.0),
        (2, 0, 0, 0, 0, 29.0, 0.0, -1.0, 0.0),
        (1, 0, 2, -2, 2, 29.0, 0.0, -12.0, 0.0),
        (2, 0, 2, 0, 2, -31.0, 0.0, 13.0, 0.0),
    ]

    dpsi = 0.0
    deps = 0.0
    u = 1e-4 / 3600.0  # degrees per 0.1-mas unit
    for (nl, nlp, nf, nd, nom, sp, spt, ce, cet) in terms:
        arg = nl * l + nlp * lp + nf * f + nd * d + nom * om
        s = sp + spt * t
        c = ce + cet * t
        if s != 0.0:
            dpsi += s * math.sin(arg)
        if c != 0.0:
            deps += c * math.cos(arg)

    return dpsi * u, deps * u


def true_obliquity_deg(jde: float) -> float:
    """True obliquity = mean obliquity + nutation in obliquity."""
    _, deps = nutation_deg(jde)
    return mean_obliquity_deg(jde) + deps


def mean_sidereal_time_deg(jd_ut: float) -> float:
    """Greenwich mean sidereal time in degrees (Meeus eq. 12.4)."""
    t = centuries_since_j2000_ut(jd_ut)
    theta = (
        280.46061837
        + 360.98564736629 * (jd_ut - 2451545.0)
        + 0.000387933 * t**2
        - t**3 / 38710000.0
    )
    return theta % 360.0


def apparent_sidereal_time_deg(jd_ut: float, jde: float | None = None) -> float:
    """Greenwich apparent sidereal time (Meeus eq. 12.2).

    Adds the equation of the equinoxes Delta psi * cos(eps_true). ``jde``
    defaults to JD_UT + DeltaT/86400.
    """
    if jde is None:
        from .timecore import julian_ephemeris_day

        jde = julian_ephemeris_day(jd_ut)
    dpsi, _ = nutation_deg(jde)
    eps_true = true_obliquity_deg(jde)
    return (mean_sidereal_time_deg(jd_ut) + dpsi * math.cos(math.radians(eps_true))) % 360.0
