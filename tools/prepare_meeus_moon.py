#!/usr/bin/env python3
"""Extract the Meeus ch. 47 abridged lunar tables from the pymeeus source.

The tables are Meeus, *Astronomical Algorithms*, 2nd ed., Table 47.A
(60 terms of Sigma-l / Sigma-r) and Table 47.B (60 terms of Sigma-b), an
abridgment of ELP-2000/82 (Chapront-Touze & Chapront). They are extracted
mechanically (ast.literal_eval) from the pymeeus distribution so no
coefficient is ever transcribed by hand:

    https://raw.githubusercontent.com/architest/pymeeus/master/pymeeus/Moon.py

The extracted numbers are theory data (facts); provenance records both the
original theory credit and the distribution the copy was taken from, whose
license is LGPL-3.0. Output: python/src/jyas_ephemeris/data/meeus_moon47.json
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = (
    "https://raw.githubusercontent.com/architest/pymeeus/master/pymeeus/Moon.py"
)
OUT = (
    Path(__file__).resolve().parent.parent
    / "python" / "src" / "jyas_ephemeris" / "data" / "meeus_moon47.json"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_table(source: str, name: str) -> list:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise ValueError(f"table {name} not found in source")


def main() -> int:
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as resp:  # noqa: S310
        data = resp.read()
    source = data.decode("utf-8")
    lr = extract_table(source, "PERIODIC_TERMS_LR_TABLE")
    b = extract_table(source, "PERIODIC_TERMS_B_TABLE")
    if len(lr) != 60 or len(b) != 60:
        print(f"FAIL: unexpected table sizes: lr={len(lr)} b={len(b)}", file=sys.stderr)
        return 1
    doc = {
        "provenance": {
            "source": SOURCE_URL,
            "source_sha256": sha256_bytes(data),
            "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "tables": "Meeus, Astronomical Algorithms, 2nd ed., Tables 47.A and 47.B",
            "theory": "abridged ELP-2000/82 (Meeus ch. 47); full theory: "
                      "Chapront-Touze M. & Chapront J., ELP 2000-82B",
            "distribution_license": "the copy was taken from pymeeus (LGPL-3.0); "
                                    "the extracted content is the coefficient "
                                    "data of the published tables",
            "units": {
                "lr": "[D, M, M', F, sigma_l (1e-6 deg), sigma_r (1e-3 km)]",
                "b": "[D, M, M', F, sigma_b (1e-6 deg)]",
            },
        },
        "lr": lr,
        "b": b,
    }
    OUT.write_text(json.dumps(doc, separators=(",", ":")), encoding="ascii")
    print(f"{OUT} ({OUT.stat().st_size} bytes, lr={len(lr)}, b={len(b)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
