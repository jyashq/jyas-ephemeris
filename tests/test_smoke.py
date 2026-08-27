import jyas_ephemeris


def test_package_imports():
    assert jyas_ephemeris.__version__


def test_public_api_surface():
    expected = {
        "julian_day",
        "julian_day_from_datetime",
        "datetime_from_julian_day",
        "delta_t_seconds",
        "julian_ephemeris_day",
        "mean_obliquity_deg",
        "nutation_deg",
        "true_obliquity_deg",
        "mean_sidereal_time_deg",
        "apparent_sidereal_time_deg",
        "find_kernel",
        "kernel_search_paths",
        "DEFAULT_KERNEL_NAME",
    }
    exported = set(jyas_ephemeris.__all__)
    missing = expected - exported
    assert not missing, f"public API missing: {missing}"
    for name in expected:
        assert hasattr(jyas_ephemeris, name)
