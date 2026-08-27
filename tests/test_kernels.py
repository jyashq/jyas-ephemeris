"""Kernel discovery tests: no network, no files required."""
from __future__ import annotations

import os

import pytest

from jyas_ephemeris.kernels import DEFAULT_KERNEL_NAME, find_kernel, kernel_search_paths


def test_no_kernel_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("JYAS_EPHE_KERNEL_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    assert find_kernel() is None
    assert (tmp_path / "cache" / "jyas-ephemeris" / "kernels") in kernel_search_paths()


def test_env_dir_takes_priority(monkeypatch, tmp_path):
    env_dir = tmp_path / "kernels"
    monkeypatch.setenv("JYAS_EPHE_KERNEL_DIR", str(env_dir))
    env_dir.mkdir()
    target = env_dir / DEFAULT_KERNEL_NAME
    target.write_bytes(b"not-a-real-kernel")  # existence is all find_kernel checks
    assert find_kernel() == target


def test_search_path_order(monkeypatch, tmp_path):
    first = tmp_path / "a"
    second = tmp_path / "b"
    monkeypatch.setenv("JYAS_EPHE_KERNEL_DIR", str(first))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    paths = kernel_search_paths()
    assert paths[0] == first
    assert paths[1] == tmp_path / "cache" / "jyas-ephemeris" / "kernels"
