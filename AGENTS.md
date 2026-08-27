# Agent operating notes — jyas-ephemeris

Public repo under the `jyashq` org (GitHub surface). A note here regenerates
into every file an agent writes afterwards, so keep these claims true.

## Hard boundaries

1. **No Swiss Ephemeris, ever, in any form** — no source files, headers, data
   files (`.se1` etc.), no `pyswisseph`/`swisseph` imports anywhere under
   `src/`, `tests/`, or tooling code paths. The whole point of this tree is an
   independent implementation whose permissive licence stays unencumbered;
   Swiss Ephemeris is dual-licensed AGPL/commercial, and importing it would
   forfeit exactly that. Consumers integrate engines behind adapters in their
   own trees, not here. Enforced by `tools/check-privacy.sh` and CI.
2. **No private material**: real home paths (`/home/<name>` patterns), LAN
   addresses, personal names beyond the public maintainer identity, other
   projects' names, live fixtures. Invented examples always. Run
   `tools/check-privacy.sh` before every commit; commit messages are in scope
   too. The checker also consults the owner's fleet-level term list when the
   machine has one, so never assume this file is the whole rulebook.
3. **Licence consistency is load-bearing**: `pyproject.toml`'s licence field,
   this file, README, NOTICE, and THIRD-PARTY-NOTICES.md must agree at all
   times. A prose change without its instrument change is how a wrong claim
   gets published.

## Numerical work discipline

When implementations land, they cite published algorithms (VPOP/ELP-style
series, Meeus-published methods, IAU conventions) and validate against printed
reference values with explicit tolerances. Never validate against output of
the encumbered engine inside this repo's tests — comparison harnesses belong
outside the tree.

## Bookkeeping

This repo has a row in the maintainer's licence register (kept privately)
that must move with reality: licence target, visibility, surface. Launch-gate steps were executed at commit zero;
future structural decisions go through that review first.
