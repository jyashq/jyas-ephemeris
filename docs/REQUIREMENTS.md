# Requirements — what jyas-ephemeris must satisfy

Evidence-based, surveyed 2026-08-27 from the consumer's own code
(`jyas:lib/swisseph_adapter.py`, `lib/settings.py`, and `rise_trans` call
sites). This file is the requirement record; `ARCHITECTURE.md` is the plan.

## The consumer contract (measured, not assumed)

### Bodies and values

| Element | Requirement | Evidence |
|---|---|---|
| Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn | geocentric apparent ecliptic longitude, latitude, longitude-speed | `chart_snapshot_for_jd` loops `PLANETS`, reads `xx[0], xx[1], xx[3]` |
| Rahu | true node by default, mean node configurable | `use_true_node` setting, default **True** |
| Ketu | always Rahu + 180°, latitude negated, speed negated | derived in adapter, not from the engine |
| Speeds | longitude speed required for retrograde detection | `use_speed` default True |

### Frame and ayanamsa

- **Sidereal by default** (`sidereal: True`), tropical supported as a mode.
- Ayanamsa selectable: `lahiri` (default), `true_citra`, `ss_citra`,
  `fagan_bradley`, `krishnamurti`, `raman`, `yukteshwar`. The adapter maps
  names to engine ayanamsa identifiers, so jyas-ephemeris must provide
  these seven, Lahiri first.

### Houses

- `houses_ex` with configurable system letter, default **"P" (Placidus)**.
- Returns 12 cusps + Ascendant + MC; longitudes are then assigned to houses.
- Placidus requires apparent sidereal time + true obliquity + an iterative
  semi-arc construction; whole-sign and equal systems are trivially layered
  on cusps/Asc, but "P" is the hard requirement.

### Rise/set events

- Sun rise used by `lib/yoga_report.py`, `lib/classics_report.py`,
  `lib/varshaphala.py` (×2) — with geoposition (lon, lat, alt=0.0) and the
  sidereal flags carried through.

### Time handling

- Gregorian calendar only (`swe.GREG_CAL`); Julian-date inputs are out of
  scope until a consumer asks.
- Naive ISO strings are treated as UTC by the adapter; jyas-ephemeris should
  accept ISO-with-offset and convert.
- `julday`/`revjul` round-trips and JD→ISO rendering exist in the adapter —
  keep identical rounding semantics (seconds clamp at :59, no carry).

### Kernels (already anticipated by the consumer)

- Settings carry `prefer_jpl` and `jpl_file`; default empty/off. So the
  optional JPL tier maps onto an existing switch — the bootstrap helper only
  needs to fetch a kernel and the settings need a path.

## What typical software wants (general feature matrix)

Standard ephemeris-library expectations, and their status here:

| Feature | Needed by jyas? | Status |
|---|---|---|
| JD ↔ calendar conversions, UTC/UT1/TT | yes | timecore (this increment) |
| ΔT (UT1−TT) model | yes (all modern positions) | timecore |
| Sidereal time / obliquity / nutation | yes (houses, rise/set) | earth (this increment) |
| Sun position | yes | planned: VSOP87D-truncated |
| Moon position | yes | planned: ELP2000-derived truncated series |
| Mercury–Saturn positions | yes | planned: VSOP87D-truncated |
| Lunar node (true + mean) | yes (Rahu/Ketu) | planned: mean = simple; true = series |
| Ayanamsa family (7 systems) | yes | planned after precession model |
| Placidus houses | yes | planned after sidereal time + obliquity |
| Sunrise/sunset | yes | planned: altitude-scan + refraction |
| Tithi/nakshatra/dasha boundary timing | yes (dasha engine) | planned: interval scan + bisection |
| Moon phase, retrograde flags | general | speed sign gives retrograde; phase planned |
| JPL SPK kernel reading | optional | kernels module + fetch helper (this increment) |

## Accuracy targets

- Consumer need: sign/nakshatra boundary robustness at arcminute scale;
  parity target with the incumbent engine at arcsecond scale for
  Sun/Moon/planets over 1900–2100.
- Tier 1 (built-in series): **MEASURED 2026-08-27 against DE440s apparent
  ecliptic-of-date longitudes, 504 samples over 1900-2100**: worst error
  Sun 0.46″, Venus 0.46″, Mercury 0.50″, Mars 0.59″, Saturn 0.77″,
  Jupiter 1.07″. Residual = VSOP87's DE200 fit vs DE440 plus the
  documented truncation budgets - far inside every boundary the consumer
  computes (a nakshatra pada is 200″).
- Moon (Meeus ch. 47 abridged ELP-2000/82): **MEASURED 2026-08-27 against
  DE440s, 168 samples over 1900-2100**: worst apparent-longitude error
  10.67″ - the published accuracy class of the abridgment, inside target.
  True node (osculating, analytic-derivative method): worst 0.47′ vs the
  incumbent engine's osculating node; mean node matches to ±0.3′.
- Ayanamsa (all seven consumer systems): **MEASURED 2026-08-27 against the
  incumbent engine's ayanamsa implementation, 1900-2100 decade sweep**:
  worst error ≤17.8″ for the six constant-anchored systems (Lahiri,
  Fagan/Bradley, Raman, Krishnamurti, Yukteshwar, SS Citra — residual =
  the incumbent's per-system historical precession models vs our uniform
  IAU 2006), and **0.55″ worst / 1.8″ fine for True Citra** (star-computed
  Spica, Simbad astrometry, ERFA-construction IAU 2006 matrix).
- Houses (Placidus sidereal, 5 dates × 5 sites vs the incumbent): worst
  16.7″ — entirely the ayanamsa layer above; the house geometry itself
  agrees to ≤0.06″ tropical. Rise/set: worst 10.4 s over 36 aligned cases
  including ±64° polar-edge sites (residual = the incumbent's fine
  threshold structure; its effective h0 measured at -0.874 deg, which is
  our default). Tithi ends: 2-9 s near-term, ~105 s at the 2100 edge
  (Moon-truncation scale); Vimshottari layout is exact integer
  arithmetic.
- Tier 2 (JPL DE440s when installed): ~mas-class positions; also the
  validation reference for Tier 1 acceptance.
- ΔT: Espenak–Meeus polynomials (±~1 s over 1900–2150; 1 s ≈ 0.5″ of Moon
  motion — inside budget).
- Nutation: IAU 1980 series, 20 of 106 terms (< 0.01″ residual), full
  table drops in behind the same signature.

## Explicitly out of scope until asked

- Julian-calendar dates, heliocentric outputs, topocentric parallax
  correction, asteroid/uranian bodies, SWIEPH data files (forbidden — see
  README/NOTICE).
