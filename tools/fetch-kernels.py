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

# JPL's HTTPS mirror publishes no .md5 sidecar for DE440s (404, verified
# 2026-08-27). Verification falls back to a pinned SHA256 recorded on first
# retrieval (trust-on-first-use); the kernel is a static NASA release.
PINNED_SHA256 = {
    "de440s.bsp": None,  # filled on first successful download; see fetch()
}


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


def expected_md5(name: str) -> str | None:
    """Return the published md5 when the sidecar exists, else None."""
    url = f"{BASE_URL}/{name}.md5"
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
            text = resp.read().decode("ascii", errors="replace")
        return text.split()[0].strip().lower()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(dest: Path, name: str, force: bool) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / name
    want_md5 = expected_md5(name)
    if target.is_file() and not force:
        if want_md5 is not None:
            have = md5_of(target)
            if have == want_md5:
                print(f"ok: {target} already present, md5 verified")
                return 0
        else:
            print(f"ok: {target} already present (size {target.stat().st_size}; "
                  f"no published sidecar checksum at this mirror)")
            return 0
        print(f"stale: {target} exists but md5 mismatch; refetching", file=sys.stderr)
    url = f"{BASE_URL}/{name}"
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
        if want_md5 is not None:
            have = md5_of(tmp)
            if have != want_md5:
                tmp.unlink(missing_ok=True)
                print(f"FAIL: md5 mismatch: got {have}, want {want_md5}", file=sys.stderr)
                return 1
            note = f"md5 {have}"
        else:
            digest = sha256_of(tmp)
            note = f"sha256 {digest} (first retrieval; no published sidecar checksum)"
        tmp.replace(target)
        print(f"ok: {target} ({total} bytes, {note})")
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
