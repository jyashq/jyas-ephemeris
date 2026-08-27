"""Panchanga boundaries and the Vimshottari reference layout.

Boundary timing: all classical elements are linear functions of lunar and
solar apparent longitudes; each boundary is a crossing of a target angle
by a signed difference. `find_crossing` scans a coarse grid, then
bisections to sub-second precision.

Vimshottari: this module provides the REFERENCE layout (lord order, year
lengths, mahadasha/antardasha spans) and the balance-at-birth computation.
The consumer's dasha engine owns its own period logic; the engine swap only
needs astronomical positions plus these arithmetic primitives.

⛔ Convention note (a measured lesson of the consumer's stack): the
Vimshottari year is 365.0 days in the consumer's engine, not the mean
tropical year. The default here matches that convention explicitly.
"""
from __future__ import annotations

import math

from .positions import apparent_longitude_deg

__all__ = [
    "find_crossing",
    "lunar_longitude_diff",
    "tithi_info",
    "nakshatra_info",
    "yoga_info",
    "vimshottari_balance",
    "vimshottari_mahadashas",
    "VIMSHOTTARI_LORDS",
    "VIMSHOTTARI_YEARS",
    "NAKSHATRA_LORDS",
]

VIMSHOTTARI_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
VIMSHOTTARI_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}
NAKSHATRA_LORDS = VIMSHOTTARI_LORDS  # Ashwini begins with Ketu

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
    "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
    "Trayodashi", "Chaturdashi", "Purnima", "Pratipada", "Dwitiya",
    "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami",
    "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi",
    "Chaturdashi", "Amavasya",
]


def lunar_longitude_diff(jd_ut: float) -> float:
    """(Moon - Sun) apparent longitude difference in [0, 360)."""
    moon = apparent_longitude_deg("moon", jd_ut)
    sun = apparent_longitude_deg("sun", jd_ut)
    return (moon - sun) % 360.0


def find_crossing(
    value_fn,
    target_deg: float,
    jd_start: float,
    jd_end: float,
    step_days: float = 0.25,
) -> float:
    """First UT Julian day in [jd_start, jd_end] where ``value_fn(jd)``
    crosses ``target_deg`` (mod-360 crossing, forward direction).

    The crossing manifests as a WRAP of the mod-360 value: just before the
    boundary the value sits just under 360 increasing, just after it is
    just past 0 — so a true crossing is a LARGE DROP (cur << prev), never
    a rise. Raises ValueError if no crossing is found.
    """
    prev = (value_fn(jd_start) - target_deg) % 360.0
    if prev == 0.0:
        return jd_start
    n = max(2, int(math.ceil((jd_end - jd_start) / step_days)))
    for i in range(1, n + 1):
        jd = jd_start + (jd_end - jd_start) * i / n
        cur = (value_fn(jd) - target_deg) % 360.0
        if cur == 0.0:
            return jd
        if prev - cur > 180.0:  # wrapped forward through the target
            lo, hi = jd_start + (jd_end - jd_start) * (i - 1) / n, jd
            flo = prev
            for _ in range(50):
                mid = 0.5 * (lo + hi)
                fmid = (value_fn(mid) - target_deg) % 360.0
                if fmid > 180.0:  # still pre-wrap: root is ahead
                    lo, flo = mid, fmid
                else:  # past the wrap: root is behind
                    hi = mid
            return 0.5 * (lo + hi)
        prev = cur
    raise ValueError(f"no crossing of {target_deg} deg in [{jd_start}, {jd_end}]")


def _mono_diff(jd: float) -> float:
    return lunar_longitude_diff(jd)


def tithi_info(jd_ut: float, ayanamsa: None = None) -> dict:
    """Tithi index (1..30), name, and the UT Julian day of its end.

    Tithi k (1-based) runs while the Moon-Sun difference is in
    [(k-1)*12, k*12). Index and end are frame-consistent: the difference
    uses apparent longitudes (the consumer's sidereal setting cancels in
    the Moon-Sun difference).
    """
    diff = lunar_longitude_diff(jd_ut)
    index = int(diff // 12.0) + 1  # 1..30
    target = index * 12.0
    end = find_crossing(_mono_diff, target, jd_ut, jd_ut + 3.0)
    name = TITHI_NAMES[index - 1]
    paksha = "Shukla" if index <= 15 else "Krishna"
    return {"index": index, "name": name, "paksha": paksha, "end_jd_ut": end}


def nakshatra_info(jd_ut: float, sidereal_system: str = "lahiri") -> dict:
    """Nakshatra index (1..27), name, lord, and the end time, for the
    sidereal Moon longitude."""
    from .ayanamsa import ayanamsa_deg

    jde = None
    moon = apparent_longitude_deg("moon", jd_ut)
    jde_tt = jd_ut  # ayanamsa uses TT; difference below 0.01" over a day — pass through
    ayan = ayanamsa_deg(sidereal_system, jde_tt)
    sid = (moon - ayan) % 360.0
    span = 360.0 / 27.0
    index = int(sid // span) + 1
    target = index * span
    end = find_crossing(
        lambda j: (apparent_longitude_deg("moon", j) - ayanamsa_deg(sidereal_system, j)) % 360.0,
        target,
        jd_ut,
        jd_ut + 2.0,
    )
    lord = NAKSHATRA_LORDS[(index - 1) % 9]
    return {
        "index": index,
        "name": NAKSHATRA_NAMES[index - 1],
        "lord": lord,
        "end_jd_ut": end,
    }


def yoga_info(jd_ut: float, sidereal_system: str = "lahiri") -> dict:
    """Nitya yoga: index (1..27), name, end time. Value = (Moon + Sun)/span."""
    from .ayanamsa import ayanamsa_deg

    def value(j):
        s = apparent_longitude_deg("sun", j)
        m = apparent_longitude_deg("moon", j)
        return (m + s - ayanamsa_deg(sidereal_system, j)) % 360.0

    v = value(jd_ut)
    span = 360.0 / 27.0
    index = int(v // span) + 1
    end = find_crossing(value, index * span, jd_ut, jd_ut + 2.0)
    return {"index": index, "name": NAKSHATRA_NAMES[index - 1], "end_jd_ut": end}


def vimshottari_balance(
    jd_ut: float,
    sidereal_system: str = "lahiri",
    year_length_days: float = 365.0,
    span_years: float = 120.0,
) -> dict:
    """Vimshottari mahadasha balance at ``jd_ut`` from the sidereal Moon.

    Returns the running lord, its full span, elapsed and remaining days,
    the sequence of (lord, start_jd, end_jd) mahadashas covering
    ``span_years``, and the start/end of the whole cycle.
    """
    from .ayanamsa import ayanamsa_deg

    ayan = ayanamsa_deg(sidereal_system, jd_ut)
    sid = (apparent_longitude_deg("moon", jd_ut) - ayan) % 360.0
    span = 360.0 / 27.0
    nak_index = int(sid // span) + 1
    lord0 = NAKSHATRA_LORDS[(nak_index - 1) % 9]
    nak_end_lon = nak_index * span
    fraction_remaining = (nak_end_lon - sid) / span
    year0 = VIMSHOTTARI_YEARS[lord0]
    span0_days = year0 * year_length_days
    remaining_days = fraction_remaining * span0_days
    start_jd = jd_ut - (span0_days - remaining_days)

    # Full mahadasha sequence from cycle start
    seq = []
    lord_i = VIMSHOTTARI_LORDS.index(lord0)
    t = start_jd
    total_days = span_years * year_length_days
    while t < start_jd + total_days:
        lord = VIMSHOTTARI_LORDS[lord_i % 9]
        dur = VIMSHOTTARI_YEARS[lord] * year_length_days
        seq.append((lord, t, t + dur))
        t += dur
        lord_i += 1
    return {
        "balance_lord": lord0,
        "balance_span_days": span0_days,
        "balance_elapsed_days": span0_days - remaining_days,
        "balance_remaining_days": remaining_days,
        "cycle_start_jd_ut": start_jd,
        "cycle_end_jd_ut": start_jd + total_days,
        "mahadashas": seq,
    }


def vimshottari_mahadashas(
    jd_ut: float,
    sidereal_system: str = "lahiri",
    year_length_days: float = 365.0,
    span_years: float = 120.0,
) -> list[tuple[str, float, float]]:
    """Convenience: the mahadasha (lord, start, end) list."""
    return vimshottari_balance(
        jd_ut, sidereal_system, year_length_days, span_years
    )["mahadashas"]
