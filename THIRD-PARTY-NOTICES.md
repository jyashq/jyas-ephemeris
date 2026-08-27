# Third-party notices

This repository bundles no third-party *code*. Two vendored *data* files
carry third-party theory tables:

- `python/src/jyas_ephemeris/data/vsop87d_*.json` — truncated VSOP87D
  series, theory by Bretagnon & Francou (Bureau des Longitudes), generated
  from the IMCCE public distribution; provenance in each file.
- `python/src/jyas_ephemeris/data/meeus_moon47.json` — the abridged lunar
  tables of Meeus, *Astronomical Algorithms*, 2nd ed., Tables 47.A/47.B
  (an abridgment of ELP-2000/82 by Chapront-Touzé & Chapront), extracted
  from the pymeeus distribution (LGPL-3.0; the extracted content is the
  published coefficient data). Provenance in the file.

Rule: nothing lands as vendored/bundled material without (1) a licence
compatible with Apache-2.0 *for this act of redistribution*, (2) an
entry here naming upstream, version, licence, and local path, and (3) a
line in the root `NOTICE`. Dependency-level use (declared in
`pyproject.toml`) also needs the compatibility check, and anything
copyleft is refused outright if it would cross the boundary described in
README ("Licensing notes").
