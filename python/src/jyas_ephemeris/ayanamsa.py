"""Sidereal frames: the seven consumer ayanamsa systems.

Method (mirroring the geometry the incumbent engines use): the vernal
point of date is precessed back to the system's anchor epoch t0 (via
J2000), rotated onto the ecliptic of t0, and the ayanamsa is the anchor
value a0 minus the resulting longitude:

    ayanamsa(date) = a0 - lambda(vernal point of date | expressed at t0)

Precession: IAU 2006 equatorial angles zeta_A, z_A, theta_A (Capitaine &
Wallace 2006, as tabulated by SOFA/ERFA p06e). The incumbent applies
per-system historical precession models (Newcomb, IAU 1976, Vondrak) with
a correction term between models; using one modern model uniformly leaves
residual per-system differences against the incumbent of order arcseconds
over 1900-2100, measured and documented in tests/test_ayanamsa.py and
docs/REQUIREMENTS.md. A nakshatra pada is 200 arcseconds.

The seven systems (anchor values as published in the incumbent's
documentation):

    lahiri         t0=2435553.5      a0=23.250182778 - 0.004658035
    fagan_bradley  t0=2433282.42346  a0=24.042044444
    raman          t0=J1900          a0=360 - 338.98556
    krishnamurti   t0=J1900          a0=360 - 337.636111
    yukteshwar     t0=J1900          a0=360 - 338.917778
    ss_citra       t0=1903396.8128654 a0=2.11070444  (true equinox)
    true_citra     Spica at exactly 180 deg sidereal, star-computed

True Citra uses the star: Spica's Hipparcos-era ICRS astrometry (Simbad,
2007A&A...474..653V), propagated with proper motion, precessed to date,
aberrated, and referred to the true ecliptic and equinox of date.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .earth import nutation_deg, true_obliquity_deg
from .timecore import _J2000_JD  # noqa: F401  (documentation constant)

__all__ = [
    "SYSTEMS",
    "ayanamsa_deg",
    "sidereal_longitude_deg",
    "spica_longitude_deg",
]

_DAS2R = math.pi / (180.0 * 3600.0)
_J1900 = 2415020.0

SYSTEMS = {
    "lahiri": {"t0": 2435553.5, "a0": 23.250182778 - 0.004658035},
    "fagan_bradley": {"t0": 2433282.42346, "a0": 24.042044444},
    "raman": {"t0": _J1900, "a0": 360.0 - 338.98556},
    "krishnamurti": {"t0": _J1900, "a0": 360.0 - 337.636111},
    "yukteshwar": {"t0": _J1900, "a0": 360.0 - 338.917778},
    "ss_citra": {"t0": 1903396.8128654, "a0": 2.11070444},
    "true_citra": {"t0": 0.0, "a0": 0.0},  # star-computed, see below
}

_SPICA_DATA = Path(__file__).resolve().parent / "data" / "spica_simbad.json"
_C_AU_PER_DAY = 173.1446326846693


def _rz(mat, psi):
    """SOFA iauRz: left-multiply by [[c, s, 0], [-s, c, 0], [0, 0, 1]]."""
    c, s = math.cos(psi), math.sin(psi)
    r = [list(row) for row in mat]
    for j in range(3):
        a0 = c * r[0][j] + s * r[1][j]
        a1 = -s * r[0][j] + c * r[1][j]
        r[0][j], r[1][j] = a0, a1
    return tuple(tuple(row) for row in r)


def _rx(mat, phi):
    """SOFA iauRx: left-multiply by [[1, 0, 0], [0, c, s], [0, -s, c]]."""
    c, s = math.cos(phi), math.sin(phi)
    r = [list(row) for row in mat]
    for j in range(3):
        a1 = c * r[1][j] + s * r[2][j]
        a2 = -s * r[1][j] + c * r[2][j]
        r[1][j], r[2][j] = a1, a2
    return tuple(tuple(row) for row in r)


_OBL06 = (84381.406, -46.836769, -0.0001831, 0.00200340, -0.000000576, -0.0000000434)


def _obliquity06_deg(jde_tt: float) -> float:
    """IAU 2006 mean obliquity (eraObl06 polynomial), degrees."""
    t = (jde_tt - 2451545.0) / 36525.0
    c = _OBL06
    arcsec = c[0] + (c[1] + (c[2] + (c[3] + (c[4] + c[5] * t) * t) * t) * t) * t
    return arcsec / 3600.0


def _precession_matrix(jde_tt: float) -> tuple[tuple[float, ...], ...]:
    """IAU 2006 bias-precession matrix, GCRS(J2000) -> mean equator/equinox
    of date, built exactly as ERFA's pmat06: pfw06 angles (Fukushima-
    Williams, with their real constant bias terms) followed by fw2m's
    R = Rx(-eps) . Rz(-psi) . Rx(phi) . Rz(gam). Orientation is verified
    in tests against published values and the DE440s/oracle sweep.
    """
    t = (jde_tt - 2451545.0) / 36525.0

    def poly(c):
        return (
            c[0]
            + (c[1] + (c[2] + (c[3] + (c[4] + c[5] * t) * t) * t) * t) * t
        ) * _DAS2R

    gamb = poly((-0.052928, 10.556378, 0.4932044, -0.00031238, -0.000002788, 0.0000000260))
    phib = poly((84381.412819, -46.811016, 0.0511268, 0.00053289, -0.000000440, -0.0000000176))
    psib = poly((-0.041775, 5038.481484, 1.5584175, -0.00018522, -0.000026452, -0.0000000148))
    epsa = math.radians(_obliquity06_deg(jde_tt))

    r = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    r = _rz(r, gamb)
    r = _rx(r, phib)
    r = _rz(r, -psib)
    r = _rx(r, -epsa)
    return r


def _apply(m, v):
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


def _transpose_apply(m, v):
    return (
        m[0][0] * v[0] + m[1][0] * v[1] + m[2][0] * v[2],
        m[0][1] * v[0] + m[1][1] * v[1] + m[2][1] * v[2],
        m[0][2] * v[0] + m[1][2] * v[1] + m[2][2] * v[2],
    )


def _ecliptic_lon_of_frame(date_frame_vec: tuple[float, float, float], jde_tt: float) -> float:
    """Rotate an equatorial-of-date vector onto the ecliptic of date and
    return its longitude."""
    eps = math.radians(_mean_obliquity_deg_cached(jde_tt))
    y = date_frame_vec[1] * math.cos(eps) + date_frame_vec[2] * math.sin(eps)
    x = date_frame_vec[0]
    return math.degrees(math.atan2(y, x))


_OBLIQUITY_CACHE: dict[float, float] = {}


def _mean_obliquity_deg_cached(jde_tt: float) -> float:
    # Local import to avoid a module-level cycle; earth.py is a sibling.
    from .earth import mean_obliquity_deg

    key = round(jde_tt, 6)
    if key not in _OBLIQUITY_CACHE:
        _OBLIQUITY_CACHE[key] = mean_obliquity_deg(jde_tt)
    return _OBLIQUITY_CACHE[key]


def ayanamsa_deg(system: str, jde_tt: float) -> float:
    """Ayanamsa (degrees) of ``system`` at a Julian Ephemeris Day.

    ayanamsa = a0 + p_A(date) - p_A(t0), with p_A the IAU 2006 general
    precession in longitude (Capitaine & Wallace; the polynomial verified
    against p06e to < 0.000001 deg at 1 century). This is the
    ecliptic-of-date-consistent formulation: the value subtracts cleanly
    from apparent longitudes referred to the equinox and ecliptic of date.
    Mean-equinox convention (subtract from apparent longitudes for the
    sidereal value; the incumbent subtracts the same way).
    """
    if system == "true_citra":
        # The incumbent's star path carries annual aberration; supply the
        # Earth's heliocentric velocity for the first-order term.
        from .positions import _vec

        h = 0.1
        e0 = _vec("earth", jde_tt - h)
        e1 = _vec("earth", jde_tt + h)
        vel = (
            (e1[0] - e0[0]) / (2 * h),
            (e1[1] - e0[1]) / (2 * h),
            (e1[2] - e0[2]) / (2 * h),
        )
        return (spica_longitude_deg(jde_tt, earth_vel_au_day=vel) - 180.0) % 360.0
    if system not in SYSTEMS:
        raise ValueError(f"unknown ayanamsa system: {system!r}")
    s = SYSTEMS[system]
    return (s["a0"] + _pa_deg(jde_tt) - _pa_deg(s["t0"])) % 360.0


def _pa_deg(jde_tt: float) -> float:
    """IAU 2006 general precession in longitude, degrees from J2000."""
    t = (jde_tt - 2451545.0) / 36525.0
    arcsec = (
        5028.796195
        + (1.1054348 + (0.00007964 + (-0.000023857 + (-0.0000000383 * t)) * t) * t) * t
    ) * t
    return arcsec / 3600.0


def sidereal_longitude_deg(
    apparent_tropical_lon_deg: float, system: str, jde_tt: float
) -> float:
    """Convert an apparent tropical longitude to sidereal for ``system``."""
    return (apparent_tropical_lon_deg - ayanamsa_deg(system, jde_tt)) % 360.0


def _spica_astrometry() -> dict:
    with _SPICA_DATA.open("r", encoding="ascii") as fh:
        return json.load(fh)


def spica_longitude_deg(jde_tt: float, earth_vel_au_day: tuple[float, float, float] | None = None) -> float:
    """Apparent ecliptic longitude of Spica (true equinox and ecliptic of date).

    Astrometry pinned from Simbad (ICRS J2000, 2007A&A...474..653V) in
    data/spica_simbad.json. Proper motion is applied; parallax (13 mas)
    and radial velocity are below the budget and not applied. Annual
    aberration is applied with the caller-supplied Earth velocity when
    given (au/day, same frame convention as positions.py); without it the
    aberration term is skipped (documented ~20 arcsecond scale effect).
    """
    astro = _spica_astrometry()
    ra0 = astro["ra_deg"]
    dec0 = astro["dec_deg"]
    pmra = astro["pmra_masyr"]   # mas/yr in RA * cos(dec)
    pmdec = astro["pmdec_masyr"]  # mas/yr
    dt_yr = (jde_tt - 2451545.0) / 365.25
    dec = dec0 + pmdec / 3.6e6 * dt_yr
    ra = ra0 + pmra / 3.6e6 * dt_yr / max(1e-9, math.cos(math.radians(dec)))

    cd = math.cos(math.radians(dec))
    v_icrs = (
        cd * math.cos(math.radians(ra)),
        cd * math.sin(math.radians(ra)),
        math.sin(math.radians(dec)),
    )
    # ICRS ~ J2000 equatorial at our precision; precess to date.
    # R is the ERFA-construction bias-precession matrix, GCRS(J2000) ->
    # mean-of-date; a fixed star gains ~50.29 arcsec/year of ecliptic
    # longitude under it (verified against the DE440s-oracle sweep).
    n = _apply(_precession_matrix(jde_tt), v_icrs)

    if earth_vel_au_day is not None:
        n = tuple(n[i] + earth_vel_au_day[i] / _C_AU_PER_DAY for i in range(3))
        norm = math.sqrt(sum(c * c for c in n))
        n = tuple(c / norm for c in n)

    # True ecliptic of date: rotate by true obliquity, add nutation in longitude.
    eps_true = math.radians(true_obliquity_deg(jde_tt))
    lam = math.atan2(
        n[1] * math.cos(eps_true) + n[2] * math.sin(eps_true),
        n[0],
    )
    dpsi, _ = nutation_deg(jde_tt)
    return math.degrees(lam + math.radians(dpsi)) % 360.0
