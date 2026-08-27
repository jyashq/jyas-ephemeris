# jyas-ephemeris

An independent ephemeris computation core in pure Python: planetary positions,
sidereal conversions, calendar primitives, and the deterministic arithmetic
used in panchanga calendrics — tithi, nakshatra, yoga, karana, and dasha
period timelines.

Developed as part of the [JYAS](https://github.com/jyashq) ecosystem.
Status: **early scaffold** — the instrument set below is stable, computation
lands incrementally.

## Design principles

- **Independent implementation.** Algorithms are implemented from published
  sources (standard astronomical series and conventions, printed reference
  tables). The repository intentionally contains no third-party engine code —
  see [Licensing](#licensing).
- **Zero runtime dependencies.** Pure standard-library Python.
- **Reproducible numerics.** Every function names the algorithm it implements
  and validates against printed reference values with explicit tolerances;
  invented references are not validation.
- **Checked boundaries.** Tooling refuses personal-data shapes and off-licence
  dependencies before they can land (`tools/check-privacy.sh`, enforced in CI).

## Licensing notes

This project is licensed Apache-2.0. It does not include, link, vendor, or
depend on Swiss Ephemeris source or data files, which Astrodienst distributes
under its own terms (AGPL-3.0 or a professional licence). Implementing from
published algorithms is what keeps this codebase unencumbered and freely
usable, including in products with their own licensing terms. Consumers who
want an encumbered engine integrate it in their own projects, behind their own
adapters — not here.

The boundary is mechanical, not aspirational: CI runs `tools/check-privacy.sh`,
which rejects Swiss Ephemeris files, imports, and vendored data alongside
personal-information checks.

## Planned scope (0.x)

| Area | Status |
|---|---|
| Calendar / Julian-day primitives, Delta T | **0.1.0** |
| Sidereal time, obliquity, nutation | **0.1.0** |
| Sun + Mercury–Saturn apparent positions (VSOP87D) | **0.1.0** |
| Moon + lunar nodes (Meeus abridged ELP-2000/82) | **0.2.0** |
| Ayanamsa conversions (7 systems, Lahiri default) | **0.3.0** |
| Optional JPL kernel tier (DE440s fetch + discovery) | **0.1.0** (discovery + fetch helper) |
| Panchanga elements (tithi, nakshatra, yoga, karana) | planned |
| Dasha period arithmetic | planned |
| Placidus houses, sunrise/sunset | planned |

## Installation

From source (packaging on PyPI follows the first computation release):

```sh
python3 -m pip install .
```

Usage documentation lands with the first computation release.

## Development

The Python prototype lives under `python/`; it is the reference
implementation whose behaviour the future Rust core must reproduce
(`docs/ARCHITECTURE.md`).

```sh
cd python
python3 -m pip install -e . pytest
python3 -m pytest tests/ -q
../tools/check-privacy.sh     # run before every commit
```

Optional JPL kernel for the validation tier:

```sh
tools/fetch-kernels.py        # DE440s into the cache dir, md5-verified
```

## Contributing

Contributions are welcome under a signed CLA before first merge; see
[CONTRIBUTING.md](CONTRIBUTING.md) and [CLA.md](CLA.md). You keep your
copyright.

## License

- Code: [Apache License 2.0](LICENSE)
- Documentation: [CC-BY-SA-4.0](LICENSE-CC-BY-SA-4.0)

## Trademarks

JYAS and associated marks are trademarks of Avikalpa Kundu, under common-law
rights pending registration. These licenses do not grant trademark rights;
see [TRADEMARKS.md](TRADEMARKS.md).
