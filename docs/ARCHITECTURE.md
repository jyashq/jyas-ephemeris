# Architecture

## Shape

A pure-Python, dependency-free computation core with an optional,
explicitly-isolated JPL kernel tier.

```
timecore        JD/calendar, UTC→TT (ΔT), GREG_CAL round-trips
earth           GMST/apparent sidereal time, obliquity (mean/true),
                nutation (truncated lunisolar), future: full IAU table
positions/      VSOP87D-truncated Sun+planets, ELP-derived Moon, nodes
ayanamsa        precession model + the seven consumer ayanamsa systems
houses          Placidus (iterative semi-arc), then trivial systems
events          rise/set (refraction model), tithi/nakshatra root-finding
kernels         optional DE440s discovery/loading (jplephem extra)
```

Every module states the published algorithm it implements in its docstring
and every numerical claim in tests cites a printed reference value with an
explicit tolerance. No exceptions.

## The two tiers

1. **Tier 1 — built-in analytic series** (always available, zero deps):
   truncated VSOP87-class planetary theory, truncated lunar series, standard
   time-scale models. Arcsecond-class for planets, ~10″-class for the Moon.
   This covers every boundary the consumer computes (sign, nakshatra, tithi,
   dasha) with large margin.
2. **Tier 2 — JPL kernels** (opt-in): DE440s SPK fetched by
   `tools/fetch-kernels.py`, read via the optional `jplephem` extra.
   Millesisecond-class truth; used (a) by consumers who want it, via the
   same `prefer_jpl`/`jpl_file` settings the consumer already carries, and
   (b) as the acceptance reference for Tier 1 in development harnesses that
   live OUTSIDE this repository.

Kernel files are never committed; the fetch helper stores them under a
cache directory (`$JYAS_EPHE_KERNEL_DIR` or `~/.cache/jyas-ephemeris/`) with
checksum verification, and is idempotent.

## Data-source provenance (licence-cleanliness is the product)

| Component | Source | Status |
|---|---|---|
| Planetary series | VSOP87 (Bretagnon & Francou, Bureau des Longitudes), public releases; truncated subsets | to be vendored with attribution + provenance note when positions land |
| Lunar series | ELP2000-82B derivatives (Chapront), published truncated versions | same discipline |
| ΔT | Espenak & Meeus polynomial set (NASA GSFC published formulas) | implemented, cited |
| Sidereal time / obliquity | Meeus, *Astronomical Algorithms* 2nd ed. formulas; Laskar (1986) obliquity | implemented, cited |
| Nutation | IAU 1980 model (Explanatory Supplement, Seidelmann 1992, s. 3.222); fundamental arguments in SOFA convention, leading 20 of 106 terms (< 0.01 arcsecond residual) | implemented, cited |
| JPL kernels | DE440s, NASA/JPL public domain | fetched at runtime, never committed |

⛔ The tree must never contain Swiss Ephemeris source, headers, `.se1/.se2`
data, or bindings of them — enforced by `tools/check-privacy.sh` (which also
refuses personal-data shapes). Integration of encumbered engines belongs to
consumers, behind adapters in their own trees.

## Numerical conventions

- Longitudes in degrees in the public API (matches the consumer), radians
  internally where the math wants them; every public function documents
  which.
- Terrestrial time: UT1≈UTC (ΔUT1 ≤ 0.9 s absorbed into ΔT model);
  TT↔TDB difference (< 2 ms → < 0.0001″) ignored, documented.
- Apparent positions include light-time? For geocentric apparent longitudes
  at arcsecond scale: annual aberration for Sun/planets and light-time for
  the Moon are part of the planned position pipeline; documented per-body
  when it lands.

## Testing posture

- In-repo tests: fast, closed-form references (worked examples from
  published texts, self-consistency, round-trips). No network.
- Kernel-dependent tests: skipped unless a kernel is present
  (`JYAS_EPHE_KERNEL_DIR` or cache default).
- Cross-engine parity harnesses (against the incumbent engine or JPL truth)
  live OUTSIDE the repo, in the consumer's tree, per AGENTS.md.
