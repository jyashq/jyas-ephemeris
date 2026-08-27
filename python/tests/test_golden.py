"""Golden-vector contract tests: the committed oracle file must reproduce.

These double as the prototype's own regression net and as the definition
of what the Rust core must satisfy (same file, same tolerances).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from jyas_ephemeris.ayanamsa import ayanamsa_deg
from jyas_ephemeris.houses import houses
from jyas_ephemeris.moon import mean_node_deg, true_node_deg
from jyas_ephemeris.panchanga import nakshatra_info, tithi_info
from jyas_ephemeris.positions import (
    BODIES,
    apparent_speed_longitude_deg_per_day,
    geocentric_apparent,
)
from jyas_ephemeris.timecore import julian_ephemeris_day

GOLDEN = Path(__file__).resolve().parent.parent / "golden" / "golden_v1.json"
DOC = json.loads(GOLDEN.read_text())
TOL = DOC["provenance"]["tolerances"]


@pytest.mark.parametrize("vector", DOC["vectors"], ids=lambda v: f"jd{v['jd_ut']}")
def test_golden_vector(vector):
    jd = vector["jd_ut"]
    jde = julian_ephemeris_day(jd)
    for body, want in vector["bodies"].items():
        p = geocentric_apparent(body, jd_ut=jd)
        assert p.longitude_deg == pytest.approx(want["lon"], abs=TOL["lon_deg"])
        assert p.latitude_deg == pytest.approx(want["lat"], abs=TOL["lat_deg"])
        assert p.distance_au == pytest.approx(want["dist"], abs=TOL["dist_au"])
        speed = apparent_speed_longitude_deg_per_day(body, jd)
        assert speed == pytest.approx(want["speed"], abs=TOL["speed_deg_per_day"])

    h = houses(jd, 17.0, 78.0, "P", sidereal_system="lahiri")
    for got, want in zip(h["cusps"], vector["houses"]["cusps"]):
        assert got == pytest.approx(want, abs=TOL["cusps_deg"])
    assert h["ascendant"] == pytest.approx(vector["houses"]["asc"], abs=TOL["cusps_deg"])
    assert h["mc"] == pytest.approx(vector["houses"]["mc"], abs=TOL["cusps_deg"])

    assert ayanamsa_deg("lahiri", jde) == pytest.approx(
        vector["ayanamsa_lahiri"], abs=TOL["ayanamsa_deg"]
    )
    assert true_node_deg(jde) == pytest.approx(
        vector["moon_nodes"]["true"], abs=TOL["nodes_deg"]
    )
    assert mean_node_deg(jde) == pytest.approx(
        vector["moon_nodes"]["mean"], abs=TOL["nodes_deg"]
    )
    assert tithi_info(jd)["index"] == vector["tithi_index"]
    assert nakshatra_info(jd, "lahiri")["index"] == vector["nakshatra_index"]
