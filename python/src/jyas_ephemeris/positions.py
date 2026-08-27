"""Geocentric apparent positions: Sun and Mercury through Saturn.

Sources and references:
- Series data: VSOP87D (Bretagnon & Francou, Astron. Astrophys. 202, 309,
  1988), heliocentric spherical variables, dynamical ecliptic and equinox
  OF DATE, fitted by its authors to JPL DE200 (1 arcsecond-class over
  millennia; see the IMCCE notice vsop87.doc). The vendored JSON files under
  data/ are truncated from the IMCCE D4 distribution by explicit
  dropped-amplitude budgets recorded in each file's provenance block, and
  tools/prepare_vsop87.py regenerates them.
- Evaluation: term = T^alpha * A * cos(B + C*T), T in millennia from J2000
  (vsop87.doc "COMPUTATION").
- Pipeline per Meeus, *Astronomical Algorithms*, 2nd ed.:
  light-time iteration (ch. 33 style), annual aberration as the vector
  correction n - v_E/c (first order), VSOP-to-FK5 frame correction
  (ch. 32, eq. 32.3), apparent place by adding nutation in longitude
  (ch. 22).

Tropical apparent longitudes of date. The sidereal layer (ayanamsa) is a
separate module; the consumer applies the two in sequence.

Bodies: sun, mercury, venus, mars, jupiter, saturn. Earth itself is the
observer; the Moon is a separate theory family (later increment).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from .earth import nutation_deg
from .timecore import julian_ephemeris_day

__all__ = [
    "BODIES",
    "heliocentric_spherical_rad",
    "geocentric_apparent",
    "apparent_longitude_deg",
    "apparent_speed_longitude_deg_per_day",
]

BODIES = ("sun", "mercury", "venus", "earth", "mars", "jupiter", "saturn")
_FILE_FOR = {
    "mercury": "vsop87d_mer.json",
    "venus": "vsop87d_ven.json",
    "earth": "vsop87d_ear.json",
    "mars": "vsop87d_mar.json",
    "jupiter": "vsop87d_jup.json",
    "saturn": "vsop87d_sat.json",
}

C_AU_PER_DAY = 173.1446326846693  # speed of light, au/day (IAU)
_J2000 = 2451545.0
_TJY = 365250.0  # days per julian millennium
_VSOP_TO_FK5_L = math.radians(-0.09033 / 3600.0)  # Meeus eq. 32.3 constants
_VSOP_TO_FK5_C = math.radians(0.03916 / 3600.0)

_cache: dict[str, dict] = {}
_DATA_DIR = Path(__file__).resolve().parent / "data"


def _load(body: str) -> dict:
    if body not in _cache:
        path = _DATA_DIR / _FILE_FOR[body]
        with path.open("r", encoding="ascii") as fh:
            _cache[body] = json.load(fh)["series"]
    return _cache[body]


def _eval_series(
    series: dict[str, list[list[float]]], t_mill: float
) -> float:
    """Sum T^alpha * A * cos(B + C*T) over all alpha blocks."""
    total = 0.0
    for alpha_key, terms in series.items():
        alpha = int(alpha_key)
        tpow = t_mill**alpha
        s = 0.0
        for a, b, c in terms:
            s += a * math.cos(b + c * t_mill)
        total += tpow * s
    return total


def heliocentric_spherical_rad(
    body: str, jde_tt: float
) -> tuple[float, float, float]:
    """Heliocentric (longitude, latitude, radius) in radians/au, VSOP87D.

    Frame: dynamical ecliptic and equinox OF DATE. ``jde_tt`` is a Julian
    Ephemeris Day (TT).
    """
    if body not in _FILE_FOR:
        raise ValueError(f"unknown body for VSOP87D series: {body!r}")
    series = _load(body)
    t = (jde_tt - _J2000) / _TJY
    lon = _eval_series(series["L"], t)
    lat = _eval_series(series["B"], t)
    rad = _eval_series(series["R"], t)
    return lon, lat, rad


def _vec(body: str, jde_tt: float) -> tuple[float, float, float]:
    lon, lat, r = heliocentric_spherical_rad(body, jde_tt)
    cb = math.cos(lat)
    return (r * cb * math.cos(lon), r * cb * math.sin(lon), r * math.sin(lat))


def _fk5_correct(lon: float, lat: float) -> tuple[float, float]:
    """VSOP87-of-date to FK5 frame correction (Meeus eq. 32.3), radians in/out."""
    cl = math.cos(lon)
    sl = math.sin(lon)
    tanb = math.tan(lat)
    dlon = _VSOP_TO_FK5_L + _VSOP_TO_FK5_C * (cl + sl) * tanb
    dlat = _VSOP_TO_FK5_C * (cl - sl) * math.cos(lat)
    return lon - dlon, lat + dlat


@dataclass(frozen=True)
class ApparentPlace:
    body: str
    longitude_deg: float  # apparent, ecliptic of date, FK5-corrected
    latitude_deg: float
    distance_au: float
    light_time_days: float


def _normalize2(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    return (v[0] / n, v[1] / n, v[2] / n)


def _apparent_direction(
    body: str, jde_tt: float, earth_vel: tuple[float, float, float]
) -> tuple[tuple[float, float, float], float]:
    """Unit apparent direction (first-order) + light time, in the of-date
    VSOP87D frame, BEFORE nutation."""
    e = _vec("earth", jde_tt)
    if body == "sun":
        n = _normalize2((-e[0], -e[1], -e[2]))
        r = math.sqrt(e[0] ** 2 + e[1] ** 2 + e[2] ** 2)
        tau = r / C_AU_PER_DAY
    else:
        p = _vec(body, jde_tt)
        u = (p[0] - e[0], p[1] - e[1], p[2] - e[2])
        tau = math.sqrt(u[0] ** 2 + u[1] ** 2 + u[2] ** 2) / C_AU_PER_DAY
        # Two fixed light-time iterations (converged to < 0.01 arcsecond).
        for _ in range(2):
            p = _vec(body, jde_tt - tau)
            u = (p[0] - e[0], p[1] - e[1], p[2] - e[2])
            tau = math.sqrt(u[0] ** 2 + u[1] ** 2 + u[2] ** 2) / C_AU_PER_DAY
        n = _normalize2(u)
    # First-order annual aberration: apparent = geometric + v_obs/c (the
    # tilt toward the observer's motion); for the Sun this is the classical
    # -20.4898"/R constant of the Astronomical Almanac. Sign verified
    # against the DE440s oracle (see tests).
    v = earth_vel
    n_app = _normalize2((n[0] + v[0] / C_AU_PER_DAY, n[1] + v[1] / C_AU_PER_DAY, n[2] + v[2] / C_AU_PER_DAY))
    return n_app, tau


def geocentric_apparent(
    body: str, jd_ut: float | None = None, jde_tt: float | None = None, with_fk5: bool = True
) -> ApparentPlace:
    """Apparent geocentric place for the Sun or a planet.

    ``jd_ut`` is a Julian Day in UT1 (UTC approximation, per timecore);
    alternatively pass ``jde_tt`` directly when the dynamical instant is
    already known (tests, published examples given in TD).

    Longitude/latitude are apparent, referred to the true ecliptic and
    equinox of date (VSOP87D frame, FK5-corrected, nutation added).
    """
    if body not in BODIES or body == "earth":
        raise ValueError(f"geocentric place is defined for {BODIES} minus 'earth'")
    if jde_tt is None:
        if jd_ut is None:
            raise ValueError("provide either jd_ut or jde_tt")
        jde = julian_ephemeris_day(jd_ut)
    else:
        jde = jde_tt
    h = 0.1  # days; central difference for Earth's barycentric-ish velocity
    e0 = _vec("earth", jde - h)
    e1 = _vec("earth", jde + h)
    vel = ((e1[0] - e0[0]) / (2 * h), (e1[1] - e0[1]) / (2 * h), (e1[2] - e0[2]) / (2 * h))

    n, tau = _apparent_direction(body, jde, vel)
    lon = math.atan2(n[1], n[0])
    lat = math.asin(max(-1.0, min(1.0, n[2])))
    if with_fk5:
        lon, lat = _fk5_correct(lon, lat)
    dpsi, _ = nutation_deg(jde)
    lon = (lon + math.radians(dpsi)) % (2.0 * math.pi)

    if body == "sun":
        dist = tau * C_AU_PER_DAY
    else:
        p = _vec(body, jde - tau)
        e = _vec("earth", jde)
        dist = math.sqrt((p[0] - e[0]) ** 2 + (p[1] - e[1]) ** 2 + (p[2] - e[2]) ** 2)

    return ApparentPlace(
        body=body,
        longitude_deg=math.degrees(lon),
        latitude_deg=math.degrees(lat),
        distance_au=dist,
        light_time_days=tau,
    )


def apparent_longitude_deg(body: str, jd_ut: float) -> float:
    """Convenience: apparent geocentric longitude in degrees [0, 360)."""
    return geocentric_apparent(body, jd_ut=jd_ut).longitude_deg


def apparent_speed_longitude_deg_per_day(
    body: str, jd_ut: float, step_days: float = 0.5
) -> float:
    """d(lambda)/dt of the apparent longitude, degrees per day.

    Central difference with unwrapping (the consumer uses the speed's sign
    for retrograde determination; a day-scale step smooths opposition-day
    sign flicker the same way the incumbent engine's numeric derivative
    does not — see tests).
    """
    h = step_days
    l0 = geocentric_apparent(body, jd_ut=jd_ut - h).longitude_deg
    l1 = geocentric_apparent(body, jd_ut=jd_ut + h).longitude_deg
    dl = (l1 - l0 + 180.0) % 360.0 - 180.0
    return dl / (2.0 * h)
