"""Optional JPL kernel tier: discovery and availability only.

Reading SPK files requires the optional ``jplephem`` dependency
(`pip install 'jyas-ephemeris[jpl]'`). This module intentionally contains no
network code: kernels are fetched by ``tools/fetch-kernels.py`` (checksum
verified) and only *discovered* here.

Kernel files are never committed to the repository.
"""
from __future__ import annotations

import os
from pathlib import Path

__all__ = ["kernel_search_paths", "find_kernel"]

DEFAULT_KERNEL_NAME = "de440s.bsp"
_ENV_DIR = "JYAS_EPHE_KERNEL_DIR"


def kernel_search_paths() -> list[Path]:
    """Directories searched for JPL SPK kernels, in order."""
    paths: list[Path] = []
    env_dir = os.environ.get(_ENV_DIR, "").strip()
    if env_dir:
        paths.append(Path(env_dir).expanduser())
    cache = os.environ.get("XDG_CACHE_HOME", "").strip()
    base = Path(cache).expanduser() if cache else Path.home() / ".cache"
    paths.append(base / "jyas-ephemeris" / "kernels")
    return paths


def find_kernel(name: str = DEFAULT_KERNEL_NAME) -> Path | None:
    """Return the first existing kernel file named ``name``, or None."""
    for directory in kernel_search_paths():
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None
