#!/usr/bin/env python3
"""Minimal MCP (Model Context Protocol) stdio server for jyas-ephemeris.

Speaks newline-delimited JSON-RPC 2.0 over stdin/stdout per the MCP stdio
transport: initialize -> tools/list -> tools/call. Pure stdlib; reads the
prototype package. Tools:

    positions        body longitudes/latitudes/distances/speeds
    chart_snapshot   planets + Placidus houses + nodes + tithi/nakshatra
    panchanga        tithi / nakshatra / yoga details at an instant
    dasha_balance    Vimshottari balance + mahadasha timeline

Every result is deterministic astronomy; the server holds no state and no
data beyond the vendored theory tables. Logs go to stderr, never stdout.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python" / "src"))

from jyas_ephemeris.ayanamsa import ayanamsa_deg  # noqa: E402
from jyas_ephemeris.houses import houses  # noqa: E402
from jyas_ephemeris.moon import mean_node_deg, true_node_deg  # noqa: E402
from jyas_ephemeris.panchanga import nakshatra_info, tithi_info, vimshottari_balance  # noqa: E402
from jyas_ephemeris.positions import (  # noqa: E402
    BODIES,
    apparent_speed_longitude_deg_per_day,
    geocentric_apparent,
)
from jyas_ephemeris.timecore import (  # noqa: E402
    datetime_from_julian_day,
    julian_day,
    julian_ephemeris_day,
)

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "jyas-ephemeris", "version": "0.4.0"}

TOOLS = [
    {
        "name": "positions",
        "description": (
            "Apparent geocentric ecliptic longitudes/latitudes/distances and "
            "longitude speeds for sun, moon, mercury, venus, mars, jupiter, "
            "saturn (tropical, of date)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "jd_ut": {"type": "number", "description": "Julian day, UT"},
                "bodies": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["jd_ut"],
        },
    },
    {
        "name": "chart_snapshot",
        "description": (
            "Full chart snapshot: sidereal longitudes of the seven planets "
            "plus Rahu/Ketu, Placidus cusps, Ascendant, MC for a latitude/"
            "longitude, ayanamsa, nodes, tithi and nakshatra."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "jd_ut": {"type": "number"},
                "lat": {"type": "number"},
                "lon_east": {"type": "number"},
                "sidereal_system": {
                    "type": "string",
                    "enum": sorted([
                        "lahiri", "true_citra", "ss_citra", "fagan_bradley",
                        "krishnamurti", "raman", "yukteshwar",
                    ]),
                    "description": "default: lahiri",
                },
                "true_node": {"type": "boolean", "description": "default true"},
            },
            "required": ["jd_ut", "lat", "lon_east"],
        },
    },
    {
        "name": "panchanga",
        "description": "Tithi, nakshatra (with lords) and their end instants.",
        "inputSchema": {
            "type": "object",
            "properties": {"jd_ut": {"type": "number"}},
            "required": ["jd_ut"],
        },
    },
    {
        "name": "dasha_balance",
        "description": (
            "Vimshottari mahadasha balance and timeline (default year length "
            "365.0 days, the consumer engine's convention)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "jd_ut": {"type": "number"},
                "year_length_days": {"type": "number"},
            },
            "required": ["jd_ut"],
        },
    },
]


def _iso(jd: float) -> str:
    return datetime_from_julian_day(jd).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _resolve_instant(args: dict) -> float:
    if "jd_ut" in args:
        return float(args["jd_ut"])
    if "iso" in args:
        dt = datetime.fromisoformat(str(args["iso"]))
        return julian_day(dt.year, dt.month, dt.day,
                          dt.hour + dt.minute / 60 + dt.second / 3600)
    raise ValueError("provide jd_ut or iso")


def tool_positions(args: dict) -> dict:
    jd_ut = _resolve_instant(args)
    want = args.get("bodies") or [b for b in BODIES if b != "earth"]
    out = {"jd_ut": jd_ut, "utc": _iso(jd_ut), "bodies": {}}
    for b in want:
        if b not in BODIES or b == "earth":
            raise ValueError(f"unknown body: {b}")
        p = geocentric_apparent(b, jd_ut=jd_ut)
        out["bodies"][b] = {
            "longitude": round(p.longitude_deg, 8),
            "latitude": round(p.latitude_deg, 8),
            "distance_au": round(p.distance_au, 9),
            "speed_longitude": round(apparent_speed_longitude_deg_per_day(b, jd_ut), 8),
        }
    return out


def tool_chart_snapshot(args: dict) -> dict:
    jd_ut = _resolve_instant(args)
    lat = float(args["lat"])
    lon = float(args["lon_east"])
    sid = str(args.get("sidereal_system", "lahiri"))
    jde = julian_ephemeris_day(jd_ut)
    ayan = ayanamsa_deg(sid, jde)
    h = houses(jd_ut, lat, lon, "P", sidereal_system=sid)
    bodies = {}
    for b in ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"):
        p = geocentric_apparent(b, jd_ut=jd_ut)
        lon_sid = (p.longitude_deg - ayan) % 360.0
        speed = apparent_speed_longitude_deg_per_day(b, jd_ut)
        entry = {
            "longitude_sidereal": round(lon_sid, 8),
            "longitude_tropical": round(p.longitude_deg, 8),
            "speed_longitude": round(speed, 8),
            "retrograde": speed < 0,
            "sign": int(lon_sid // 30.0) + 1,
            "degree_in_sign": round(lon_sid % 30.0, 8),
        }
        bodies[b] = entry
    use_true = bool(args.get("true_node", True))
    rahu = true_node_deg(jde) if use_true else mean_node_deg(jde)
    ketu = (rahu + 180.0) % 360.0
    bodies["Rahu"] = {"longitude_sidereal": round(rahu, 8),
                      "sign": int(rahu // 30.0) + 1, "node_type": "true" if use_true else "mean"}
    bodies["Ketu"] = {"longitude_sidereal": round(ketu, 8),
                      "sign": int(ketu // 30.0) + 1, "derived_from": "Rahu+180"}
    t = tithi_info(jd_ut)
    nk = nakshatra_info(jd_ut, sid)
    return {
        "jd_ut": jd_ut, "utc": _iso(jd_ut), "lat": lat, "lon_east": lon,
        "sidereal_system": sid, "ayanamsa": round(ayan, 8),
        "bodies": bodies,
        "houses": {"cusps": [round(c, 8) for c in h["cusps"]],
                   "ascendant": round(h["ascendant"], 8), "mc": round(h["mc"], 8)},
        "tithi": {"index": t["index"], "name": t["name"], "paksha": t["paksha"],
                  "end_jd_ut": round(t["end_jd_ut"], 8)},
        "nakshatra": {"index": nk["index"], "name": nk["name"], "lord": nk["lord"],
                      "end_jd_ut": round(nk["end_jd_ut"], 8)},
    }


def tool_panchanga(args: dict) -> dict:
    jd_ut = _resolve_instant(args)
    t = tithi_info(jd_ut)
    nk = nakshatra_info(jd_ut)
    return {
        "jd_ut": jd_ut, "utc": _iso(jd_ut),
        "tithi": t, "nakshatra": nk,
    }


def tool_dasha_balance(args: dict) -> dict:
    jd_ut = _resolve_instant(args)
    yl = float(args.get("year_length_days", 365.0))
    v = vimshottari_balance(jd_ut, year_length_days=yl)
    return {
        "jd_ut": jd_ut,
        "balance_lord": v["balance_lord"],
        "balance_remaining_days": round(v["balance_remaining_days"], 8),
        "cycle_start_jd_ut": round(v["cycle_start_jd_ut"], 8),
        "cycle_end_jd_ut": round(v["cycle_end_jd_ut"], 8),
        "mahadashas": [
            {"lord": l, "start_jd_ut": round(s, 8), "end_jd_ut": round(e, 8),
             "start_utc": _iso(s), "end_utc": _iso(e)}
            for l, s, e in v["mahadashas"]
        ],
    }


DISPATCH = {
    "positions": tool_positions,
    "chart_snapshot": tool_chart_snapshot,
    "panchanga": tool_panchanga,
    "dasha_balance": tool_dasha_balance,
}


def handle(msg: dict) -> dict | None:
    method = msg.get("method")
    msg_id = msg.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }}
    if method is None or method.startswith("notifications/"):
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        try:
            result = DISPATCH[name](params.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": msg_id, "result": {
                "content": [{"type": "text",
                             "text": json.dumps(result, indent=1)}],
                "isError": False,
            }}
        except KeyError:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {
                "code": -32602, "message": f"unknown tool: {name!r}"}}
        except Exception as exc:  # tool errors surface as results, not crashes
            return {"jsonrpc": "2.0", "id": msg_id, "result": {
                "content": [{"type": "text", "text": str(exc)}], "isError": True}}
    return {"jsonrpc": "2.0", "id": msg_id, "error": {
        "code": -32601, "message": f"unknown method: {method!r}"}}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            reply = handle(msg)
        except Exception as exc:  # never crash the server on one message
            reply = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {
                "code": -32603, "message": str(exc)}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
