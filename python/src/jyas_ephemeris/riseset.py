"""Sunrise and sunset for the consumer's daily-timing needs.

Model: the apparent Sun (positions.py pipeline) crosses altitude h0.
Default h0 = -0.874 deg — the MEASURED effective threshold of the
incumbent engine's rise/set routine (its refraction + semidiameter
handling), with the classical -0.8333 deg available as an override.

Semantics: `sun_rise_set` returns the NEXT upward crossing (rise) and the
NEXT downward crossing (set) strictly after the start instant, each found
independently by sign-change scan + bisection. Near the polar circles a
crossing may not exist within the search span; the result then reports
None and a polar classification rather than a fabricated time.
"""
from __future__ import annotations

import math

from .earth import apparent_sidereal_time_deg, true_obliquity_deg
from .positions import geocentric_apparent

__all__ = ["sun_rise_set", "sun_transit", "sun_altitude"]


def sun_altitude(jd_ut: float, lat_deg: float, lon_east_deg: float) -> float:
    """Apparent geocentric altitude of the Sun (degrees), no refraction."""
    lam = geocentric_apparent("sun", jd_ut=jd_ut).longitude_deg
    eps = math.radians(true_obliquity_deg(jd_ut))
    lam_r = math.radians(lam)
    dec = math.asin(math.sin(eps) * math.sin(lam_r))
    ra = math.atan2(math.cos(eps) * math.sin(lam_r), math.cos(lam_r))
    lst = math.radians((apparent_sidereal_time_deg(jd_ut) + lon_east_deg) % 360.0)
    phi = math.radians(lat_deg)
    sin_h = (
        math.sin(phi) * math.sin(dec)
        + math.cos(phi) * math.cos(dec) * math.cos(lst - ra)
    )
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_h))))


# Backwards-compatible private alias used by earlier drafts/tests.
def _altitude(jd_ut: float, lat_deg: float, lon_east_deg: float) -> float:
    return sun_altitude(jd_ut, lat_deg, lon_east_deg)


def _ra_rate_correction(jd_ut: float, lon_east_deg: float) -> float:
    """Day-fraction Newton step toward LST(t) = RA(t)."""
    ra, _ = _sun_equatorial(jd_ut)
    lst = (apparent_sidereal_time_deg(jd_ut) + lon_east_deg) % 360.0
    d = ((ra - lst + 180.0) % 360.0) - 180.0
    return d / 360.0


def _sun_equatorial(jd_ut: float) -> tuple[float, float]:
    lam = geocentric_apparent("sun", jd_ut=jd_ut).longitude_deg
    eps = math.radians(true_obliquity_deg(jd_ut))
    lam_r = math.radians(lam)
    dec = math.asin(math.sin(eps) * math.sin(lam_r))
    ra = math.atan2(math.cos(eps) * math.sin(lam_r), math.cos(lam_r))
    return math.degrees(ra) % 360.0, math.degrees(dec)


def sun_transit(jd_ut: float, lat_deg: float, lon_east_deg: float) -> float:
    """UT Julian day of the next local solar transit strictly after
    ``jd_ut``. (Latitude does not affect the transit; kept in the
    signature for symmetry with the rest of the module.)"""
    t = jd_ut + 0.6  # pre-advance past the next transit before refining
    for attempt in range(4):
        for _ in range(6):
            step = _ra_rate_correction(t, lon_east_deg)
            t += step
            if abs(step) < 1e-8:
                break
        if t > jd_ut:
            return t
        t = jd_ut + 0.6 + attempt * 0.25
    raise ValueError("transit search failed to converge past the start instant")


def _crossing_after(
    jd_ut: float,
    lat_deg: float,
    lon_east_deg: float,
    h0_deg: float,
    want_rise: bool,
) -> float | None:
    """First crossing of alt=h0 after ``jd_ut``; upward if want_rise else
    downward. None when none occurs within the search span."""
    step = 0.05
    span = 4.0
    t = jd_ut
    f = sun_altitude(t, lat_deg, lon_east_deg) - h0_deg
    if f == 0.0:
        return t
    n = int(span / step)
    for i in range(1, n + 1):
        t2 = jd_ut + i * step
        f2 = sun_altitude(t2, lat_deg, lon_east_deg) - h0_deg
        if f2 == 0.0:
            return t2
        if f * f2 < 0:
            # bisect inside [t, t2]
            lo, hi = t, t2
            flo = f
            root = 0.5 * (lo + hi)
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                fmid = sun_altitude(mid, lat_deg, lon_east_deg) - h0_deg
                if fmid == 0.0:
                    return mid
                if (flo < 0) == (fmid < 0):
                    lo, flo = mid, fmid
                else:
                    hi = mid
                root = 0.5 * (lo + hi)
            upward = f < 0
            if upward == want_rise:
                return root
            # Wrong kind: continue the scan from this crossing.
            t, f = root, 1e-9 if upward else -1e-9
            continue
        t, f = t2, f2
    return None


def sun_rise_set(
    jd_ut: float,
    lat_deg: float,
    lon_east_deg: float,
    h0_deg: float = -0.8740,
) -> dict:
    """Next sunrise and sunset strictly after ``jd_ut``.

    Default h0 is the incumbent engine's measured effective threshold
    (-0.874 deg: its refraction + semidiameter handling); the classical
    Almanac value (-0.8333 deg) can be passed explicitly.

    Returns {"rise", "set", "polar"} where rise/set are UT Julian days or
    None, and "polar" is None or "day"/"night" when a crossing does not
    exist within the search span.
    """
    rise = _crossing_after(jd_ut, lat_deg, lon_east_deg, h0_deg, want_rise=True)
    set_ = _crossing_after(jd_ut, lat_deg, lon_east_deg, h0_deg, want_rise=False)
    polar = None
    if rise is None or set_ is None:
        mid = jd_ut + 2.0
        polar = "day" if sun_altitude(mid, lat_deg, lon_east_deg) > h0_deg else "night"
    return {"rise": rise, "set": set_, "polar": polar}
