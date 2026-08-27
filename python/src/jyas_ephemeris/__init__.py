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
from .moon import (
    apparent_moon,
    geometric_ecliptic_deg,
    mean_node_deg,
    true_node_deg,
)
from .ayanamsa import (
    SYSTEMS,
    ayanamsa_deg,
    sidereal_longitude_deg,
    spica_longitude_deg,
)
from .houses import houses, houses_armc
from .riseset import sun_rise_set, sun_transit, sun_altitude
from .panchanga import (
    find_crossing,
    tithi_info,
    nakshatra_info,
    yoga_info,
    vimshottari_balance,
    vimshottari_mahadashas,
)

__version__ = "0.4.0"

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
    "apparent_moon",
    "geometric_ecliptic_deg",
    "mean_node_deg",
    "true_node_deg",
    "SYSTEMS",
    "ayanamsa_deg",
    "sidereal_longitude_deg",
    "spica_longitude_deg",
    "houses",
    "houses_armc",
    "sun_rise_set",
    "sun_transit",
    "sun_altitude",
    "find_crossing",
    "tithi_info",
    "nakshatra_info",
    "yoga_info",
    "vimshottari_balance",
    "vimshottari_mahadashas",
    "find_kernel",
    "kernel_search_paths",
    "DEFAULT_KERNEL_NAME",
]
