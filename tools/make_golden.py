#!/usr/bin/env python3
"""Generate the golden vector file (the prototype <-> Rust contract).

Emits python/golden/golden_v1.json: full deterministic snapshots at
SYNTHETIC timestamps spread over 1900-2100 (no personal data, no real
birth data). The Rust core must reproduce every value within the
tolerances recorded in the file; this prototype is the oracle.

Regenerate ONLY when the prototype's own anchors change; the file is a
contract, not a cache. Any regeneration must be noted in the commit that
changes the physics.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python" / "src"))

from jyas_ephemeris.ayanamsa import ayanamsa_deg  # noqa: E402
from jyas_ephemeris.houses import houses  # noqa: E402
from jyas_ephemeris.moon import mean_node_deg, true_node_deg  # noqa: E402
from jyas_ephemeris.panchanga import nakshatra_info, tithi_info  # noqa: E402
from jyas_ephemeris.positions import (  # noqa: E402
    BODIES,
    apparent_speed_longitude_deg_per_day,
    geocentric_apparent,
)
from jyas_ephemeris.timecore import julian_day  # noqa: E402

LAT, LON = 17.0, 78.0  # synthetic neutral site (no real location)
SIDEREAL = "lahiri"


def snap(jd_ut: float) -> dict:
    bodies = {}
    for b in BODIES:
        if b == "earth":
            continue
        p = geocentric_apparent(b, jd_ut=jd_ut)
        bodies[b] = {
            "lon": round(p.longitude_deg, 8),
            "lat": round(p.latitude_deg, 8),
            "dist": round(p.distance_au, 9),
            "speed": round(apparent_speed_longitude_deg_per_day(b, jd_ut), 8),
        }
    h = houses(jd_ut, LAT, LON, "P", sidereal_system=SIDEREAL)
    t = tithi_info(jd_ut)
    nk = nakshatra_info(jd_ut, SIDEREAL)
    return {
        "jd_ut": round(jd_ut, 9),
        "ayanamsa_lahiri": round(ayanamsa_deg(SIDEREAL, julian_ephemeris_day(jd_ut)), 8),
        "bodies": bodies,
        "houses": {
            "cusps": [round(c, 8) for c in h["cusps"]],
            "asc": round(h["ascendant"], 8),
            "mc": round(h["mc"], 8),
        },
        "moon_nodes": {
            "true": round(true_node_deg(julian_ephemeris_day(jd_ut)), 8),
            "mean": round(mean_node_deg(julian_ephemeris_day(jd_ut)), 8),
        },
        "tithi_index": t["index"],
        "nakshatra_index": nk["index"],
    }


from jyas_ephemeris.timecore import julian_ephemeris_day  # noqa: E402


def main() -> int:
    instants = []
    for year in (1900, 1950, 2000, 2050, 2100):
        for month, day, hour in ((1, 15, 3.7), (4, 15, 11.25), (7, 15, 18.6), (10, 15, 9.9)):
            instants.append(julian_day(year, month, day, hour))

    doc = {
        "provenance": {
            "generator": "tools/make_golden.py",
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "oracle": "jyas-ephemeris python prototype (anchored to published "
                      "references and swept against DE440s / the incumbent engine; "
                      "see docs/REQUIREMENTS.md)",
            "site": {"lat": LAT, "lon": LON, "note": "synthetic neutral site"},
            "sidereal_system": SIDEREAL,
            "tolerances": {
                "lon_deg": 0.003, "lat_deg": 0.003, "dist_au": 1e-7,
                "speed_deg_per_day": 0.0001, "cusps_deg": 0.003,
                "ayanamsa_deg": 0.001, "nodes_deg": 0.02,
                "indices": 0,
            },
            "purpose": "acceptance contract for the Rust core (crates/); "
                       "the Rust CI must reproduce every value within tolerance",
        },
        "vectors": [snap(j) for j in instants],
    }
    out = Path(__file__).resolve().parent.parent / "python" / "golden" / "golden_v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1), encoding="ascii")
    print(f"{out} ({out.stat().st_size} bytes, {len(instants)} vectors)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
