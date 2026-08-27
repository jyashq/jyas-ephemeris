#!/usr/bin/env bash
# Refuse to let private material — or encumbered engine code — into this PUBLIC repo.
#
# Adapted from yggterm's scripts/check-privacy.sh and its measured lessons;
# see that file for the full history of each failure these checks exist to
# prevent. The two leak vectors this tree guards:
#
#   1. THE PERSONAL MAP. Never a credential — an agent writing a REAL example
#      (a home path, an LAN address, a private project's name) into a fixture,
#      doc line, or commit because a real example was in front of it. Use
#      invented examples. Always.
#
#   2. THE ENGINE BOUNDARY. This repository may stay Apache-2.0 only while it
#      contains zero Swiss Ephemeris source, data files, or bindings, which
#      are dual-licensed AGPL/professional by their copyright holder. One
#      import or one vendored .c file forfeits the whole licence posture, so
#      this checker refuses them mechanically rather than trusting review.
#
# ⛔ This checker must not itself become the leak. It matches SHAPES where it
# can, and where it must name something it holds the term base64-encoded, so
# the word is not greppable in a public tree. Never add a plaintext private
# term below.
#
# Exit non-zero with the offending lines; silence means clean.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
fail=0
note() { echo "privacy: $*" >&2; fail=1; }

# Tracked files AND untracked-but-not-ignored ones, minus third-party trees
# and binary-ish assets.
#
# ⛔ UNTRACKED FILES ARE IN SCOPE ON PURPOSE: this checker runs BEFORE a
# commit, and before a commit a newly written doc is exactly `??`. Scanning
# tracked files alone reports "ok" on a leaky file nobody added yet — the one
# moment the lock exists to cover was the one moment it could not see.
files=$(git ls-files --cached --others --exclude-standard \
  | grep -vE '^(vendor|third_party|node_modules)/' \
  | grep -vE '\.(png|jpg|jpeg|ico|gz|zip)$' \
  | grep -vE '^tools/check-privacy\.sh$')
[ -n "$files" ] || exit 0

hits() { echo "$files" | xargs grep -nIE "$1" 2>/dev/null; }

# 1. Personal home paths. A public repo must not know whose machine it was on.
#    ⛔ No trailing slash required: a bare `/home/<name>` at a word boundary
#    went straight through an earlier detector of exactly this shape.
#    ⛔ Allowlisting is PER MATCH, never per line: blank placeholders out
#    FIRST, then ask whether any home path remains — `grep -v` drops a whole
#    line, so a line quoting BOTH a real path and a placeholder would be
#    laundered clean by whatever sat next to the real path.
PLACEHOLDER='/home/(user|u|x|y|z|operator|gui-host|example|someone|test|alice|bob|dev|dev-host|build|runner|ubuntu|ci)(/|\b)'
HOMEPATH='(^|[^a-zA-Z0-9_.-])/home/[a-z][a-z0-9_-]*'
h=$(hits "$HOMEPATH" | sed -E "s#$PLACEHOLDER#<placeholder>#g" | grep -E "$HOMEPATH")
[ -n "$h" ] && { note "absolute personal home paths — use /home/user or an invented placeholder:"; echo "$h" | head -12 >&2; }

# 2. RFC1918 addresses. Real topology is a signpost to live attack surface;
#    RFC 5737 (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) exists for docs.
h=$(hits '\b(192\.168\.[0-9]+\.[0-9]+|10\.[0-9]+\.[0-9]+\.[0-9]+|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]+\.[0-9]+)\b')
[ -n "$h" ] && { note "private LAN addresses — use RFC 5737 ranges in examples:"; echo "$h" | head -12 >&2; }

# 3. Named private stores / projects / corpora, held base64-encoded so this
#    file does not republish them. Add new terms with:
#      printf '%s' 'theterm' | base64
#    ⚠ Terms that collide with legitimate domain vocabulary are DELIBERATELY
#    NOT here (canonical Sanskrit/jyotish words share names with private
#    repos); flagging them would false-positive on normal astrological prose,
#    and a checker that fires wrongly gets switched off — which protects
#    nothing. Those cases ride on human review plus the shared list below.
for enc in \
  cGxyZXZlcnNlZA== R2VvVmlzaW9u amlib25p c21iZnM= L3J1bi9zbWI0aw== YXZpa2FscGFfb3Bj
do
  term=$(printf '%s' "$enc" | base64 -d 2>/dev/null) || continue
  [ -n "$term" ] || continue
  h=$(echo "$files" | xargs grep -nIiF -- "$term" 2>/dev/null)
  [ -n "$h" ] && { note "a private store/project name is present (term withheld) — use an invented name:"; echo "$h" | head -6 >&2; }
done

# 3b. THE SHARED LIST, if this machine has one. The fleet pre-push guard keeps
#     its terms outside every repo; reading them here means a term added in
#     either place is enforced in both. The encoded floor above stays — it is
#     what protects a CI runner or fresh clone where the shared list does not
#     exist, and it must never be thinned on the assumption that the shared
#     list covers it. ⛔ Terms are never echoed; only offending lines are shown.
shared_terms="$HOME/.config/ygg-privacy/private-terms.txt"
if [ -r "$shared_terms" ]; then
  while IFS= read -r term; do
    case "$term" in ''|'#'*) continue ;; esac
    term=$(printf '%s' "$term" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [ ${#term} -ge 4 ] || continue   # too short to match without false positives
    h=$(echo "$files" | xargs grep -nIiF -- "$term" 2>/dev/null)
    [ -n "$h" ] && { note "a private name from the shared guard list is present (term withheld) — use an invented name:"; echo "$h" | head -6 >&2; }
  done < "$shared_terms"
fi

# 4. THE ENGINE BOUNDARY — Swiss Ephemeris in any form.
code_dirs='^(src|tests|tools|benches)/'
code_files=$(printf '%s\n' "$files" | grep -E "$code_dirs")

# 4a. A file NAMED like engine source, or shaped like engine data, wherever it sits.
h=$(printf '%s\n' "$files" | grep -iE '(sweph|swisseph|swe_[a-z_]+)|\.(se1|se2|sem)$')
[ -n "$h" ] && { note "file path carries Swiss Ephemeris source/data naming — none may land in this repo:"; echo "$h" | head -6 >&2; }

# 4b. Engine imports/includes inside code files. Docs MAY discuss the boundary
#     (README does) — that is why this scan is scoped to code directories.
if [ -n "$code_files" ]; then
  h=$(echo "$code_files" | xargs grep -nIE '(^[[:space:]]*(import|from)[[:space:]]+(pyswisseph|swisseph|sweph)\b|#include[[:space:]]*[<"]swe|CDLL\([^)]*sweph)' 2>/dev/null)
  [ -n "$h" ] && { note "code references Swiss Ephemeris/pyswisseph — integration belongs to consumers, not this tree:"; echo "$h" | head -6 >&2; }
fi

if [ "$fail" -eq 0 ]; then
  echo "privacy: ok — no personal paths, LAN addresses, private names, or engine code"
fi
exit $fail
