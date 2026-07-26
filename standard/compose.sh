#!/usr/bin/env bash
# Compose CLAUDE.md from the shared base plus this repo's profile.
#
# The standard is authored once in standard/base.md and standard/profiles/<profile>.md.
# Every repo generates its own CLAUDE.md from them, so a dozen repos share one rulebook
# instead of a dozen diverging copies of it.
#
#   ./standard/compose.sh            # read standard/repo.env, write CLAUDE.md
#   ./standard/compose.sh --check    # regenerate in memory and diff (CI drift guard)
#   ./standard/compose.sh --stdout   # print to stdout, write nothing
#
# Exit codes: 0 ok · 1 usage/config error · 2 drift detected (--check only).
#
# repo.env is PARSED, never sourced: it is committed configuration, and a config file
# that can execute arbitrary shell is a supply-chain hole in the standard's own tooling.
# Format is strict `KEY=value`, one per line, `#` comments and blank lines allowed. The
# value is the rest of the line verbatim, minus optional surrounding quotes; it may
# contain spaces and needs no escaping.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "${here}/.." && pwd)"
env_file="${here}/repo.env"
out="${root}/CLAUDE.md"

mode="write"
case "${1:-}" in
  --check)  mode="check" ;;
  --stdout) mode="stdout" ;;
  "")       ;;
  *) echo "usage: $0 [--check|--stdout]" >&2; exit 1 ;;
esac

if [ ! -f "${env_file}" ]; then
  echo "ERROR: ${env_file} not found — copy standard/repo.env.example and fill it in" >&2
  exit 1
fi

# read_cfg KEY -> value on stdout, empty if absent. Last assignment wins.
read_cfg() {
  awk -v key="$1" '
    /^[[:space:]]*#/ { next }
    {
      i = index($0, "=")
      if (i == 0) next
      k = substr($0, 1, i - 1)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", k)
      if (k != key) next
      v = substr($0, i + 1)
      sub(/[[:space:]]+$/, "", v)
      if (v ~ /^".*"$/ || v ~ /^'"'"'.*'"'"'$/) v = substr(v, 2, length(v) - 2)
      found = v
      seen = 1
    }
    END { if (seen) print found }
  ' "${env_file}"
}

PROFILE="$(read_cfg PROFILE)"
PROJECT="$(read_cfg PROJECT)"
PKG="$(read_cfg PKG)"
TICKET_PREFIX="$(read_cfg TICKET_PREFIX)"
GROUP="$(read_cfg GROUP)"
DESCRIPTION="$(read_cfg DESCRIPTION)"
# Distribution name for a published package. Defaults to PROJECT, but a library
# inside a group almost always needs a namespaced name (project "shared" ->
# distribution "<group>-shared") or its consumers pin a name that resolves to
# nothing, or to an unrelated package on public PyPI.
DIST="$(read_cfg DIST_NAME)"
: "${DIST:=${PROJECT}}"

for v in PROFILE PROJECT PKG TICKET_PREFIX GROUP DESCRIPTION; do
  if [ -z "${!v}" ]; then
    echo "ERROR: ${v} is missing or empty in ${env_file}" >&2
    exit 1
  fi
done

# Validated because these become filenames, branch names and ticket ids downstream.
case "${PROFILE}" in
  *[!a-z-]*|"") echo "ERROR: PROFILE='${PROFILE}' must be lowercase letters and hyphens" >&2; exit 1 ;;
esac
case "${TICKET_PREFIX}" in
  *[!A-Z0-9]*|"") echo "ERROR: TICKET_PREFIX='${TICKET_PREFIX}' must be uppercase A-Z0-9" >&2; exit 1 ;;
esac

profile_file="${here}/profiles/${PROFILE}.md"
if [ ! -f "${profile_file}" ]; then
  echo "ERROR: unknown PROFILE='${PROFILE}' — no ${profile_file}" >&2
  echo "       valid profiles: $(cd "${here}/profiles" && ls ./*.md | sed 's|.*/||; s|\.md$||' | tr '\n' ' ')" >&2
  exit 1
fi

# Bash-native substitution, not sed: values may contain any character, including the
# delimiters sed would need. Placeholders are spelled @@NAME@@ so a missed one is greppable.
body="$(cat "${here}/base.md" "${profile_file}")"
body="${body//@@PROFILE@@/${PROFILE}}"
body="${body//@@PROJECT@@/${PROJECT}}"
body="${body//@@PKG@@/${PKG}}"
body="${body//@@PREFIX@@/${TICKET_PREFIX}}"
body="${body//@@GROUP@@/${GROUP}}"
body="${body//@@DESCRIPTION@@/${DESCRIPTION}}"
body="${body//@@DIST@@/${DIST}}"

if printf '%s' "${body}" | grep -q '@@'; then
  echo "ERROR: unsubstituted placeholder(s) remain — the sources use a token compose.sh does not know:" >&2
  printf '%s' "${body}" | grep -on '@@[A-Z_]*@@' | sort -u -t: -k2 >&2
  exit 1
fi

# The checksum covers the SOURCES, so reformatting the generated file is caught too.
sources_sum="$(cat "${here}/base.md" "${profile_file}" "${env_file}" | sha256sum | cut -d' ' -f1)"

generated="$(
  echo "<!-- GENERATED FILE — DO NOT EDIT."
  echo "     Sources : standard/base.md + standard/profiles/${PROFILE}.md + standard/repo.env"
  echo "     Profile : ${PROFILE}"
  echo "     Sources-SHA256: ${sources_sum}"
  echo "     Regenerate: ./standard/compose.sh"
  echo "     Edit the sources, never this file. CI fails a change where the two disagree."
  echo "-->"
  printf '%s\n' "${body}"
)"

case "${mode}" in
  stdout)
    printf '%s\n' "${generated}"
    ;;
  write)
    printf '%s\n' "${generated}" > "${out}"
    echo "wrote ${out} (profile=${PROFILE}, sources-sha256=${sources_sum:0:12}…)"
    ;;
  check)
    if [ ! -f "${out}" ]; then
      echo "ERROR: ${out} does not exist — run ./standard/compose.sh" >&2
      exit 2
    fi
    if printf '%s\n' "${generated}" | diff -u "${out}" - > /dev/null; then
      echo "OK: CLAUDE.md matches standard/ (profile=${PROFILE})"
    else
      echo "ERROR: CLAUDE.md has drifted from standard/. Diff (committed vs regenerated):" >&2
      printf '%s\n' "${generated}" | diff -u "${out}" - >&2 || true
      echo >&2
      echo "Fix: edit standard/base.md or standard/profiles/${PROFILE}.md, then run ./standard/compose.sh" >&2
      exit 2
    fi
    ;;
esac
