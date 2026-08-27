#!/usr/bin/env python3
"""Fetch the VSOP87D source files needed by jyas-ephemeris.

Downloads one file per planet from the IMCCE public distribution:

    https://ftp.imcce.fr/pub/ephem/planets/vsop87/VSOP87D.<body>

Note: IMCCE now serves these files in the grouped "D4" series format
(header + term records per Explanatory Notice vsop87.doc: multipliers,
S, K, A, B, C columns); the evaluation formula is unchanged
(T^alpha * A * cos(B + C*T), T in millennia).

Bodies: mer ven ear mar jup sat (the consumer set; Moon is a separate
series family, Uranus/Neptune/Pluto are out of scope until asked).

VSOP87: Bretagnon, P. and Francou, G., "Planetary Theories in rectangular
and spherical variables - VSOP87 solutions", Astronomy and Astrophysics
202, 309-315 (1988). Files are retrieved for validation and for the
vendored truncated derivatives produced by tools/prepare_vsop87.py; the
full-resolution raw files stay in the local cache and are NOT committed.

Storage: $JYAS_EPHE_KERNEL_DIR/../vsop87 else XDG cache, i.e.
~/.cache/jyas-ephemeris/vsop87 by default.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://ftp.imcce.fr/pub/ephem/planets/vsop87"
BODIES = ("mer", "ven", "ear", "mar", "jup", "sat")


def cache_dir() -> Path:
    env_dir = os.environ.get("JYAS_EPHE_KERNEL_DIR", "").strip()
    if env_dir:
        return Path(env_dir).expanduser().parent / "vsop87"
    cache = os.environ.get("XDG_CACHE_HOME", "").strip()
    base = Path(cache).expanduser() if cache else Path.home() / ".cache"
    return base / "jyas-ephemeris" / "vsop87"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(dest: Path, body: str, force: bool) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / f"VSOP87D.{body}"
    if target.is_file() and target.stat().st_size > 0 and not force:
        print(f"ok: {target} cached ({target.stat().st_size} bytes)")
        return 0
    url = f"{BASE_URL}/VSOP87D.{body}"
    print(f"fetching {url} ...")
    import tempfile

    fd, tmp_name = tempfile.mkstemp(prefix=f".VSOP87D.{body}.", dir=str(dest))
    tmp = Path(tmp_name)
    try:
        with urllib.request.urlopen(url, timeout=300) as resp, tmp.open("wb") as out:  # noqa: S310
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
        if tmp.stat().st_size == 0:
            print(f"FAIL: empty download for {body}", file=sys.stderr)
            return 1
        tmp.replace(target)
        print(f"ok: {target} ({target.stat().st_size} bytes, sha256 {sha256_of(target)[:16]}...)")
    finally:
        tmp.unlink(missing_ok=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", type=Path, default=cache_dir())
    ap.add_argument("--bodies", nargs="*", default=list(BODIES), choices=BODIES)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    rc = 0
    for body in args.bodies:
        rc = fetch(args.dest, body, args.force) or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
