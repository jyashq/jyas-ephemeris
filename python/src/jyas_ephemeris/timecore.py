"""Time scales and Julian-date machinery.

Conventions follow Meeus, *Astronomical Algorithms*, 2nd ed. (1998), with the
dynamical-time model from Espenak & Meeus, "Five Millennium Canon of Solar
Eclipses" (NASA/TP-2006-214141) polynomial set for Delta T = TT - UT1.

Design notes:
- UT1 is approximated by UTC (difference below 0.9 s; absorbed into the
  Delta T model). The TT-TDB difference is below 2 ms and is ignored; that
  is below 0.0001 arcsecond of lunar motion.
- All Julian dates here are astronomical (noon-based) and Gregorian. The
  consumer (jyas) uses Gregorian exclusively.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

__all__ = [
    "julian_day",
    "julian_day_from_datetime",
    "datetime_from_julian_day",
    "centuries_since_j2000_ut",
    "delta_t_seconds",
    "julian_ephemeris_day",
]

_J2000_JD = 2451545.0


def julian_day(year: int, month: int, day: int, hour: float = 0.0) -> float:
    """Julian Day (UT) for a Gregorian calendar date and decimal UT hours.

    Meeus ch. 7 (eq. 7.1 form). Valid for all Gregorian dates (1582-10-15
    onward); a ValueError is raised for earlier dates so that Julian-calendar
    inputs cannot silently corrupt results.
    """
    if month < 1 or month > 12:
        raise ValueError(f"month out of range: {month}")
    if year < 1582 or (year == 1582 and (month < 10 or (month == 10 and day < 15))):
        raise ValueError("jyas-ephemeris accepts Gregorian dates from 1582-10-15")
    y = year
    m = month
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    jd = (
        math.floor(365.25 * (y + 4716))
        + math.floor(30.6001 * (m + 1))
        + day
        + b
        - 1524.5
        + hour / 24.0
    )
    return jd


def julian_day_from_datetime(dt: datetime) -> float:
    """Julian Day (UT) from an aware or naive datetime; naive means UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    hour = dt.hour + dt.minute / 60.0 + (dt.second + dt.microsecond / 1e6) / 3600.0
    return julian_day(dt.year, dt.month, dt.day, hour)


def datetime_from_julian_day(jd: float) -> datetime:
    """Inverse of :func:`julian_day_from_datetime`; returns naive-UTC datetime.

    The time of day is computed in whole rounded seconds, so exact seconds
    round-trip byte-stably (no 19:20:59 artifacts from binary fractions).
    """
    z = math.floor(jd + 0.5)
    f = jd + 0.5 - z
    if z >= 2299161:
        alpha = math.floor((z - 1867216.25) / 36524.25)
        z += 1 + alpha - alpha // 4
    b = z + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    day_frac = b - d - math.floor(30.6001 * e) + f
    day = int(math.floor(day_frac))
    frac_of_day = day_frac - day
    seconds_total = round(frac_of_day * 86400.0)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    from datetime import timedelta

    return datetime(year, month, day, tzinfo=timezone.utc) + timedelta(
        seconds=seconds_total
    )


def centuries_since_j2000_ut(jd_ut: float) -> float:
    """Julian centuries T from J2000.0, in UT (Meeus eq. 22.1)."""
    return (jd_ut - _J2000_JD) / 36525.0


def _decimal_year(jd_ut: float) -> float:
    y, m, d_frac = _year_month_day_fraction(jd_ut)
    days_in_year = 366.0 if _is_leap(y) else 365.0
    day_of_year = (
        _day_of_year(y, m, int(d_frac)) + (d_frac - int(d_frac)) - 1.0
    )
    return y + day_of_year / days_in_year


def _is_leap(y: int) -> bool:
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _day_of_year(y: int, m: int, d: int) -> int:
    k = 1 if _is_leap(y) else 2
    return (275 * m) // 9 - k * ((m + 9) // 12) + d - 30


def _year_month_day_fraction(jd_ut: float) -> tuple[int, int, float]:
    z = math.floor(jd_ut + 0.5)
    if z >= 2299161:
        alpha = math.floor((z - 1867216.25) / 36524.25)
        z += 1 + alpha - alpha // 4
    b = z + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    day_frac = b - d - math.floor(30.6001 * e)
    day = int(math.floor(day_frac))
    month = int(e - 1 if e < 14 else e - 13)
    year = int(c - 4716 if month > 2 else c - 4715)
    return year, month, day_frac


def delta_t_seconds(jd_ut: float) -> float:
    """Delta T = TT - UT1, in seconds.

    Espenak & Meeus (2006) polynomial set, as published in the Five
    Millennium Canon and widely reproduced (e.g. in the NASA eclipse
    bulletins). Branch selection by decimal year, exactly as published.
    """
    y = _decimal_year(jd_ut)

    if 1986.0 <= y < 2005.0:
        u = y - 2000.0
        return (
            63.86
            + 0.3345 * u
            - 0.060374 * u**2
            + 0.0017275 * u**3
            + 0.000651814 * u**4
            + 0.00002373599 * u**5
        )
    if 2005.0 <= y < 2050.0:
        u = y - 2000.0
        return 62.92 + 0.32217 * u + 0.005589 * u**2
    if 2050.0 <= y < 2150.0:
        return (
            -20.0
            + 32.0 * ((y - 1820.0) / 100.0) ** 2
            - 0.5628 * (2150.0 - y)
        )
    if 1961.0 <= y < 1986.0:
        u = y - 1975.0
        return 45.45 + 1.067 * u - u**2 / 260.0 - u**3 / 718.0
    if 1941.0 <= y < 1961.0:
        u = y - 1950.0
        return 29.07 + 0.407 * u - u**2 / 233.0 + u**3 / 2547.0
    if 1920.0 <= y < 1941.0:
        u = y - 1920.0
        return 21.20 + 0.84493 * u - 0.076100 * u**2 + 0.0020936 * u**3
    if 1900.0 <= y < 1920.0:
        u = y - 1900.0
        return (
            -2.79
            + 1.494119 * u
            - 0.0598939 * u**2
            + 0.0061966 * u**3
            - 0.000197 * u**4
        )
    if 1700.0 <= y < 1800.0:
        t = y - 1700.0
        return (
            8.83
            + 0.1603 * t
            - 0.0059285 * t**2
            + 0.00013336 * t**3
            - t**4 / 1174000.0
        )
    if 1800.0 <= y < 1900.0:
        t = y - 1900.0
        return (
            13.72
            - 0.332447 * t
            + 0.0068612 * t**2
            + 0.0041116 * t**3
            - 0.00037436 * t**4
            + 0.0000121272 * t**5
            - 0.0000001699 * t**6
            + 0.000000000875 * t**7
        )
    # Outside the telescopic era: the long-term average quadratic, with the
    # published caveat that accuracy degrades to minutes before ~1600.
    u = (y - 1820.0) / 100.0
    return -20.0 + 32.0 * u**2


def julian_ephemeris_day(jd_ut: float) -> float:
    """JDE = JD + Delta T / 86400 (Meeus eq. 7.2 style)."""
    return jd_ut + delta_t_seconds(jd_ut) / 86400.0
