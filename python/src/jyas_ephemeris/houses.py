"""House cusps: Placidus (iterative semi-arc) with the standard quadrant
machinery, plus the trivial systems the consumer may select.

References: the classical Placidus construction — cusps 11, 12 trisect the
diurnal semi-arc from MC to Asc, cusps 2, 3 trisect the nocturnal arc, each
cusp lying on its own semi-arc fraction ("pole height" iteration); MC is
the ecliptic point of the local meridian (RA = RAMC); Asc is the ecliptic
intersection of the horizon. The pole-height iteration and quadrant
dispatch below implement the classical construction directly.

Conventions:
- RAMC = apparent Greenwich sidereal time + east longitude (degrees).
- Ecliptic obliquity: TRUE obliquity of date (matching the apparent
  sidereal time the RAMC is built from).
- Input/Output longitudes are TROPICAL of date; pass ``sidereal_system``
  to receive cusps reduced by that ayanamsa (same subtraction the consumer
  applies to planets).
- |latitude| >= 90 - obliquity raises ValueError (Placidus is undefined in
  the polar circle; the consumer's engine switches to Porphyry there, we
  refuse rather than silently substitute).
"""
from __future__ import annotations

import math

from .ayanamsa import ayanamsa_deg
from .earth import apparent_sidereal_time_deg, true_obliquity_deg
from .timecore import julian_ephemeris_day

__all__ = ["houses", "houses_armc"]

_VERY_SMALL = 1e-8
_MAX_ITER = 100


def _asc1(x1: float, f: float, sine: float, cose: float) -> float:
    """Ecliptic longitude of the intersection of the ecliptic with the great
    circle of pole height ``f`` crossing the equator at RA ``x1``
    (classical oblique-ascension construction; quadrant-dispatched)."""
    x1 = x1 % 360.0
    n = int(x1 / 90.0) + 1
    if abs(90.0 - f) < _VERY_SMALL:
        return 180.0
    if abs(90.0 + f) < _VERY_SMALL:
        return 0.0

    def asc2(x: float, ff: float) -> float:
        ass = -math.tan(math.radians(ff)) * sine + cose * math.cos(math.radians(x))
        sinx = math.sin(math.radians(x))
        if abs(sinx) < _VERY_SMALL:
            sinx = 0.0
        if sinx == 0.0:
            ass = -_VERY_SMALL if ass < 0 else _VERY_SMALL
            return math.degrees(math.atan2(sinx, ass)) + (360.0 if ass < 0 else 0.0)
        if ass == 0.0:
            return -90.0 if sinx < 0 else 90.0
        a = math.degrees(math.atan2(sinx, ass))
        return a + 180.0 if a < 0 else a

    if n == 1:
        ass = asc2(x1, f)
    elif n == 2:
        ass = 180.0 - asc2(180.0 - x1, -f)
    elif n == 3:
        ass = 180.0 + asc2(x1 - 180.0, -f)
    else:
        ass = 360.0 - asc2(360.0 - x1, f)
    ass %= 360.0
    for q in (90.0, 180.0, 270.0, 360.0):
        if abs(ass - q) < _VERY_SMALL:
            ass = 0.0 if q == 360.0 else q
    return ass


def houses_armc(
    armc_deg: float,
    lat_deg: float,
    obliquity_deg: float,
    system: str = "P",
) -> dict:
    """Tropical cusps 1..12, Ascendant and MC from RAMC + latitude.

    Placidus (system 'P') iterates the classical pole-height construction;
    equal ('E') and whole-sign ('W') are derived from Asc/MC without
    iteration. Whole-sign places the Ascendant's sign as house 1.
    """
    sine = math.sin(math.radians(obliquity_deg))
    cose = math.cos(math.radians(obliquity_deg))
    armc_deg %= 360.0

    mc = _asc1(armc_deg, 0.0, sine, cose)
    asc = _asc1((armc_deg + 90.0) % 360.0, lat_deg, sine, cose)

    cusps = [0.0] * 13  # 1..12
    if system == "P":
        if abs(lat_deg) >= 90.0 - obliquity_deg:
            raise ValueError("Placidus houses are undefined within the polar circle")
        tanfi = math.tan(math.radians(lat_deg))
        tand_e = math.tan(math.radians(obliquity_deg))
        a = math.degrees(math.atan(tanfi * tand_e))

        def placidus_cusp(rectasc: float, divisor: float, fh_seed: float) -> float:
            fh = fh_seed
            cusp = _asc1(rectasc, fh, sine, cose)
            for _ in range(_MAX_ITER):
                tant = math.tan(math.radians(
                    math.degrees(math.asin(sine * math.sin(math.radians(cusp))))
                ))
                if abs(tant) < _VERY_SMALL:
                    return rectasc % 360.0
                fh = math.degrees(math.atan(
                    math.sin(math.radians(math.degrees(math.asin(tanfi * tant))) / divisor)
                    / tant
                ))
                new_cusp = _asc1(rectasc, fh, sine, cose)
                diff = abs((new_cusp - cusp + 180.0) % 360.0 - 180.0)
                cusp = new_cusp
                if diff < 1e-8:
                    break
            return cusp % 360.0

        fh1 = math.degrees(math.atan(math.sin(math.radians(a / 3.0)) / tand_e))
        fh2 = math.degrees(math.atan(math.sin(math.radians(2.0 * a / 3.0)) / tand_e))
        c11 = placidus_cusp((30.0 + armc_deg) % 360.0, 3.0, fh1)
        c12 = placidus_cusp((60.0 + armc_deg) % 360.0, 1.5, fh2)
        c2 = placidus_cusp((120.0 + armc_deg) % 360.0, 1.5, fh2)
        c3 = placidus_cusp((150.0 + armc_deg) % 360.0, 3.0, fh1)
        cusps[11], cusps[12], cusps[2], cusps[3] = c11, c12, c2, c3
    elif system == "E":
        for i in range(1, 13):
            cusps[i] = (asc + (i - 1) * 30.0) % 360.0
        mc_val = mc
        return _finish(asc, mc_val, cusps, system)
    elif system == "W":
        sign0 = asc // 30.0 * 30.0
        for i in range(1, 13):
            cusps[i] = (sign0 + (i - 1) * 30.0) % 360.0
        return _finish(asc, mc, cusps, system)
    else:
        raise ValueError(f"unsupported house system: {system!r}")

    cusps[1] = asc
    cusps[10] = mc
    cusps[4] = (mc + 180.0) % 360.0
    cusps[7] = (asc + 180.0) % 360.0
    cusps[5] = (cusps[11] + 180.0) % 360.0
    cusps[6] = (cusps[12] + 180.0) % 360.0
    cusps[8] = (cusps[2] + 180.0) % 360.0
    cusps[9] = (cusps[3] + 180.0) % 360.0
    return _finish(asc, mc, cusps, system)


def _finish(asc: float, mc: float, cusps: list[float], system: str) -> dict:
    return {
        "system": system,
        "cusps": [cusps[i] for i in range(1, 13)],
        "ascendant": asc % 360.0,
        "mc": mc % 360.0,
    }


def houses(
    jd_ut: float,
    lat_deg: float,
    lon_east_deg: float,
    system: str = "P",
    sidereal_system: str | None = None,
) -> dict:
    """House cusps for a UT instant and geographic position.

    RAMC = apparent Greenwich sidereal time + east longitude; obliquity is
    the true obliquity of date. With ``sidereal_system`` the cusps, Asc
    and MC are reduced by that ayanamsa (e.g. 'lahiri'), matching what the
    consumer's engine produces for sidereal charts.
    """
    jde = julian_ephemeris_day(jd_ut)
    eps = true_obliquity_deg(jde)
    ramc = (
        apparent_sidereal_time_deg(jd_ut) + lon_east_deg
    ) % 360.0
    out = houses_armc(ramc, lat_deg, eps, system=system)
    if sidereal_system is not None:
        ayan = ayanamsa_deg(sidereal_system, jde)
        out["cusps"] = [(c - ayan) % 360.0 for c in out["cusps"]]
        out["ascendant"] = (out["ascendant"] - ayan) % 360.0
        out["mc"] = (out["mc"] - ayan) % 360.0
        out["sidereal"] = sidereal_system
    return out
