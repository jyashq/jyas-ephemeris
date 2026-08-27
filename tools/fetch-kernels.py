#!/usr/bin/env python3
"""Fetch the default JPL planetary kernel (DE440s) with checksum verification.

Downloads from the NASA/JPL public SSDS FTP mirror over HTTPS:

    https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440s.bsp   (~32 MB)
    https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440s.bsp.md5

DE440s covers 1849-2150. The files are public domain (NASA/JPL) and are
NEVER committed to this repository; they land in a cache directory:

    $JYAS_EPHE_KERNEL_DIR, else $XDG_CACHE_HOME/jyas-ephemeris/kernels,
    else ~/.cache/jyas-ephemeris/kernels

Usage:
    tools/fetch-kernels.py [--dest DIR] [--name de440s.bsp] [--force]

Idempotent: an existing, checksum-valid file is left untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

BASE_URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp"


def default_dir() -> Path:
    env_dir = os.environ.get("JYAS_EPHE_KERNEL_DIR", "").strip()
    if env_dir:
        return Path(env_dir).expanduser()
    cache = os.environ.get("XDG_CACHE_HOME", "").strip()
    base = Path(cache).expanduser() if cache else Path.home() / ".cache"
    return base / "jyas-ephemeris" / "kernels"


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def expected_md5(name: str) -> str:
    url = f"{BASE_URL}/{name}.md5"
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
        text = resp.read().decode("ascii", errors="replace")
    # The published file is "<md5hex>  <filename>" style; take the first token.
    return text.split()[0].strip().lower()


def fetch(dest: Path, name: str, force: bool) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / name
    if target.is_file() and not force:
        want = expected_md5(name)
        have = md5_of(target)
        if have == want:
            print(f"ok: {target} already present, md5 verified ({have})")
            return 0
        print(f"stale: {target} exists but md5 {have} != {want}; refetching", file=sys.stderr)
    url = f"{BASE_URL}/{name}"
    want = expected_md5(name)
    print(f"fetching {url} ...")
    tmp = Path(tempfile.mkstemp(prefix=f".{name}.", dir=str(dest))[1])
    try:
        with urllib.request.urlopen(url, timeout=600) as resp, tmp.open("wb") as out:  # noqa: S310
            total = 0
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
                total += len(chunk)
        have = md5_of(tmp)
        if have != want:
            tmp.unlink(missing_ok=True)
            print(f"FAIL: md5 mismatch: got {have}, want {want}", file=sys.stderr)
            return 1
        tmp.replace(target)
        print(f"ok: {target} ({total} bytes, md5 {have})")
    finally:
        tmp.unlink(missing_ok=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", type=Path, default=default_dir())
    ap.add_argument("--name", default="de440s.bsp")
    ap.add_argument("--force", action="store_true", help="refetch even if present and valid")
    args = ap.parse_args()
    return fetch(args.dest, args.name, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
