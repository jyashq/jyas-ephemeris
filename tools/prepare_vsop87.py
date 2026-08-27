#!/usr/bin/env python3
"""Build the vendored truncated VSOP87D series from the raw IMCCE files.

Reads the cached VSOP87D.<body> files (tools/fetch-vsop87.py), parses the
documented term-record layout (IMCCE Explanatory Notice vsop87.doc:

    term = T^alpha * A * cos(B + C*T),   T in millennia (365250 d)

with S,K,A,B,C at fixed columns; this tool uses A,B,C only), truncates each
(body, quantity, alpha) series by an explicit DROPPED-AMPLITUDE budget, and
writes one JSON file per body under python/src/jyas_ephemeris/data/.

Provenance is written into every JSON: source URL, retrieval checksum,
format, frame, budgets, and the measured dropped sums. The raw files are
never committed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BODIES = ("mer", "ven", "ear", "mar", "jup", "sat")
QUANT = {1: "L", 2: "B", 3: "R"}
# Dropped-amplitude budgets, per quantity, in native units (rad / rad / au):
# the sum of |A| over discarded terms. Random phases make the true error far
# smaller; these are strict linear bounds.
BUDGETS = {"L": 1e-7, "B": 2e-8, "R": 2e-7}
SOURCE_URL = "https://ftp.imcce.fr/pub/ephem/planets/vsop87"

HDR = re.compile(r"VARIABLE\s+(\d+)\s+\(LBR\)\s+\*T\*\*(\d+)\s+(\d+)\s+TERMS")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_raw(path: Path) -> dict[str, dict[int, list[tuple[float, float, float]]]]:
    """Return {quantity: {alpha: [(A, B, C), ...]}} from a raw D4 file."""
    series: dict[str, dict[int, list[tuple[float, float, float]]]] = {"L": {}, "B": {}, "R": {}}
    cur_q: str | None = None
    cur_a: int | None = None
    with path.open("r", encoding="ascii") as fh:
        for line in fh:
            m = HDR.search(line)
            if m:
                cur_q = QUANT[int(m.group(1))]
                cur_a = int(m.group(2))
                series[cur_q].setdefault(cur_a, [])
                continue
            if cur_q is None or len(line) < 131:
                continue
            # Fixed columns per vsop87.doc; cross-checked against split().
            a = float(line[79:97])
            b = float(line[97:111])
            c = float(line[111:131])
            toks = line.split()
            sa, sb, sc = float(toks[-5 + 2]), float(toks[-2]), float(toks[-1])
            if abs(sa - a) > 1e-12 or abs(sb - b) > 1e-12 or abs(sc - c) > 1e-12:
                raise ValueError(f"column parse mismatch in {path.name}: {line!r}")
            series[cur_q][cur_a].append((a, b, c))
    return series


def truncate(
    series: dict[int, list[tuple[float, float, float]]], budget: float
) -> tuple[list[tuple[float, float, float]], dict]:
    """Drop the smallest-amplitude tail while its |A| sum fits the budget."""
    terms = sorted(series, key=lambda t: abs(t[0]))
    dropped_sum = 0.0
    cut = 0
    for a, _b, _c in terms:
        if dropped_sum + abs(a) <= budget:
            dropped_sum += abs(a)
            cut += 1
        else:
            break
    kept = sorted(terms[cut:], key=lambda t: -abs(t[0]))
    stats = {
        "total_terms": len(terms),
        "kept_terms": len(kept),
        "dropped_terms": cut,
        "dropped_amplitude_sum": dropped_sum,
        "budget": budget,
    }
    return kept, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--raw-dir",
        type=Path,
        default=Path.home() / ".cache" / "jyas-ephemeris" / "vsop87",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent
        / "python" / "src" / "jyas_ephemeris" / "data",
    )
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    for body in BODIES:
        raw = args.raw_dir / f"VSOP87D.{body}"
        if not raw.is_file():
            print(f"skip {body}: {raw} missing (run tools/fetch-vsop87.py)", file=sys.stderr)
            continue
        parsed = parse_raw(raw)
        out_series: dict[str, dict[str, list[list[float]]]] = {}
        stats: dict[str, dict] = {}
        for q in ("L", "B", "R"):
            out_series[q] = {}
            stats[q] = {}
            for alpha, terms in sorted(parsed[q].items()):
                kept, s = truncate(terms, BUDGETS[q])
                out_series[q][str(alpha)] = [[t[0], t[1], t[2]] for t in kept]
                stats[q][str(alpha)] = s
        doc = {
            "provenance": {
                "source": f"{SOURCE_URL}/VSOP87D.{body}",
                "source_sha256": sha256_of(raw),
                "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "theory": "VSOP87 (Bretagnon & Francou, Astron. Astrophys. 202, 309, 1988)",
                "format": (
                    "IMCCE D4 series files; term = T^alpha * A * cos(B + C*T), "
                    "T in millennia (365250 d) from J2000; A in rad or au, "
                    "B rad, C rad/millennium"
                ),
                "frame": "heliocentric, dynamical ecliptic and equinox OF DATE (VSOP87D)",
                "truncation": {
                    "rule": "kept while cumulative dropped |A| <= budget, per series",
                    "budgets": BUDGETS,
                    "measured": stats,
                },
            },
            "series": out_series,
        }
        out = args.out_dir / f"vsop87d_{body}.json"
        text = json.dumps(doc, separators=(",", ":"))
        out.write_text(text, encoding="ascii")
        total_bytes += out.stat().st_size
        n_terms = sum(
            s["kept_terms"] for q in stats.values() for s in q.values()
        )
        print(f"{body}: {n_terms} terms kept -> {out} ({out.stat().st_size} bytes)")
    print(f"total vendored bytes: {total_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
