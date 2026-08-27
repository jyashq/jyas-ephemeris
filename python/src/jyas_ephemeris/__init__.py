"""jyas-ephemeris: independent ephemeris computation core.

Apache-2.0. Deliberately contains no Swiss Ephemeris code or data; see NOTICE
and README ("Why independent is load-bearing").

Modules:
- timecore: Julian dates, calendar round-trips, Delta T (UT1->TT)
- earth:    sidereal time, obliquity, nutation
- kernels:  optional JPL DE440s discovery (files via tools/fetch-kernels.py)
"""

from .timecore import (
    datetime_from_julian_day,
    delta_t_seconds,
    julian_day,
    julian_day_from_datetime,
    julian_ephemeris_day,
)
from .earth import (
    apparent_sidereal_time_deg,
    mean_obliquity_deg,
    mean_sidereal_time_deg,
    nutation_deg,
    true_obliquity_deg,
)
from .kernels import DEFAULT_KERNEL_NAME, find_kernel, kernel_search_paths
from .positions import (
    BODIES,
    apparent_speed_longitude_deg_per_day,
    apparent_longitude_deg,
    geocentric_apparent,
    heliocentric_spherical_rad,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
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
    "BODIES",
    "heliocentric_spherical_rad",
    "geocentric_apparent",
    "apparent_longitude_deg",
    "apparent_speed_longitude_deg_per_day",
    "find_kernel",
    "kernel_search_paths",
    "DEFAULT_KERNEL_NAME",
]
