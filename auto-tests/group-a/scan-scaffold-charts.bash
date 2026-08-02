#!/usr/bin/env bash
# Tier-(a) gate: the scaffold Helm charts under templates/ are rendered and scanned by
# checkov, and ANY WAY THIS CHECK COULD BECOME A NO-OP IS A FAILURE.
#
# ---------------------------------------------------------------------------------------
# The defect this exists to close
# ---------------------------------------------------------------------------------------
#
# `checkov -d .` at the repo root prints, and then stays green:
#
#   [WARNI]  Failed processing helm chart @@PROJECT@@ at dir: ./templates/service/helm.
#            Failure details: Error: YAML parse error on @@PROJECT@@/templates/deployment.yaml:
#            error converting YAML to JSON: yaml: line 4: found character that cannot start
#            any token
#
# The chart every service repo in the group is scaffolded from was therefore never scanned by
# the gate whose whole purpose is scanning charts, and nothing said so. The same run reports
# `helm scan results: Passed checks: 84`, which is the repo's OWN helm/ chart and reads exactly
# like coverage.
#
# The cause is NOT a broken template. Helm resolves the `@@PROJECT@@.fullname` helpers fine;
# `.Chart.Name` is the literal string `@@PROJECT@@`, and the RENDERED output then contains
#
#   metadata:
#     name: @@PROJECT@@        <- unquoted
#
# `@` is a reserved YAML indicator, so a plain scalar may not begin with it and the rendered
# manifest is not YAML. (Chart.yaml already quotes its own placeholder for this reason and says
# so in a comment; the templates are not quoted, and do not need to be.)
#
# A scaffold chart is not meant to be rendered before substitution. So this script substitutes
# a throwaway copy first, renders that, and scans the result — which is the shape the artefact
# actually has.
#
# ---------------------------------------------------------------------------------------
# What must fail, and why each one is here
# ---------------------------------------------------------------------------------------
#
# Restoring the scan without restoring the ALARM would fix the symptom and leave the defect.
# Every one of these is fatal, and none of them is a warning:
#
#   * zero charts discovered        -> the glob stopped matching; the check has silently become
#                                      a no-op, which is the whole bug one level up
#   * a placeholder survives        -> a token this script does not know entered a chart; the
#                                      same hard fail `standard/compose.sh` performs, and the
#                                      same one `templates/*/README.md` asks an adopter to run
#                                      (`grep -rnE '@{2}' .`)
#   * `helm template` fails         -> FATAL. Never a warning. That downgrade is the bug.
#   * checkov reports 0 resources   -> "checkov ran and found nothing" and "checkov parsed
#                                      nothing" must not look alike. That equivalence IS the
#                                      defect being fixed here
#   * checkov reports parse errors  -> same reason
#   * any failed check              -> it is a gate or it is a report; `allow_failure` and its
#                                      relatives are banned on checks (see CLAUDE.md)
#   * helm or checkov missing       -> FATAL, deliberately NOT a skip. A scoped "nothing to do"
#                                      exit is not an exception, it is a defect to remove: it
#                                      converts "the scan never ran" into a pass
#
# The last one is also why this file is `.bash` and not `.sh`: the shared functional runner
# discovers `auto-tests/group-a/**/*.sh` recursively and maps exit 77 to "skipped". This check
# must never be able to report "skipped", so it deliberately does not match that glob. It is
# run by its own blocking job in `.gitlab-ci.yml` and `.github/workflows/ci.yml`.
#
# ---------------------------------------------------------------------------------------
# Which frameworks, and why `kubernetes` alone
# ---------------------------------------------------------------------------------------
#
# The scanned file is a RENDERED, SUBSTITUTED THROWAWAY: every placeholder in it carries a
# value this script invented, not a value the repository ships. That decides the list.
#
#   kubernetes  YES — the rendered manifests are what a spawned repo deploys, and the workload
#               hardening the standard mandates (requests/limits, non-root high UID,
#               readOnlyRootFilesystem, dropped capabilities) is exactly the CKV_K8S_* family.
#               This is the entire reason the gate exists.
#
#   secrets     NO — it is an entropy detector, and on this artefact every string it could flag
#               is one of the substitution values below, so a finding would be about the
#               fixture rather than about the repository. It also cannot tell a Secret's NAME
#               from a Secret's payload: CKV_SECRET_6 ("Base64 High Entropy String") fires on
#               the name of a Kubernetes Secret, which is a reference by construction. Both
#               ways of quieting it are worse than not running it — a `# checkov:skip=` comment
#               on the PRECEDING line reports `Skipped checks: 1` for something that was never
#               a finding, and the same comment appended to the SAME line suppresses it WITHOUT
#               counting it, i.e. silently, which is the disease this ticket is about.
#               Nothing is lost: the repository's real files — `templates/*/helm/values.yaml`
#               included — are scanned by the SAST job's `checkov -d .` with every framework
#               enabled, and by gitleaks. This gate ADDS the chart's rendered output; it does
#               not replace secret scanning of the sources.
#
#   the rest    Not applicable. The artefact is Kubernetes YAML and nothing else.
#
# ---------------------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------------------
#
#   ./auto-tests/group-a/scan-scaffold-charts.bash
#
# Exit 0 = every discovered chart rendered and scanned clean. Anything else = fail.
# Requires `helm` and `checkov` on PATH; `bridgecrew/checkov:3.3.1` ships both, which is what
# both CI hosts run so the two cannot disagree.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."
root="$PWD"

die() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

# --- tooling ---------------------------------------------------------------------------
command -v helm    >/dev/null 2>&1 || die "helm is not on PATH — this check cannot run, and a check that cannot run is not a skip"
command -v checkov >/dev/null 2>&1 || die "checkov is not on PATH — this check cannot run, and a check that cannot run is not a skip"
PY="$(command -v python3 || command -v python || true)"
[ -n "${PY}" ] || die "no python interpreter on PATH — needed to read checkov's JSON summary"

echo "== tooling =="
helm version --short
checkov --version

# --- values for the scaffold placeholders ----------------------------------------------
#
# The four identity values come from `standard/repo.env`, the file the real generator reads,
# rather than from constants invented here — so the chart is exercised with the naming this
# standard actually produces (a 20-character project name, the group that owns it) instead of
# with a fixture that can drift away from it.
#
# `repo.env` is PARSED, never sourced: it is committed configuration, and a config file that
# can execute arbitrary shell is a supply-chain hole in the standard's own tooling. The format
# is the contract documented in docs/contracts.md ("standard/repo.env — the input format") and
# implemented by standard/compose.sh: strict `KEY=value`, `#` comments and blank lines allowed,
# the value is the rest of the line verbatim minus optional surrounding quotes, last wins.
# This reader must keep those semantics; if the format ever changes, both change together.
env_file="${root}/standard/repo.env"
[ -f "${env_file}" ] || die "${env_file} not found — the scaffold placeholders have no value source"

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

V_PROJECT="$(read_cfg PROJECT)"
V_PKG="$(read_cfg PKG)"
V_PREFIX="$(read_cfg TICKET_PREFIX)"
V_GROUP="$(read_cfg GROUP)"
V_DESCRIPTION="$(read_cfg DESCRIPTION)"
for v in V_PROJECT V_PKG V_PREFIX V_GROUP V_DESCRIPTION; do
  [ -n "${!v}" ] || die "${v#V_} is missing or empty in ${env_file}"
done

# `@@REGISTRY@@` and `@@PULL_SECRET@@` are deliberately NOT repo.env keys — see
# docs/contracts.md: compose.sh writes CLAUDE.md and nothing else, so a key added there would
# be read by nobody, and adding a required key breaks every existing repo.env at once. They are
# scaffold-instantiation tokens, resolved by whoever creates the new repo. This check therefore
# supplies its own representative values, and they are representative on purpose: a hyphenated
# pull-secret name is what a real one looks like, and the framework decision above is what
# keeps an entropy detector from mistaking that NAME for a payload.
V_REGISTRY="registry.example.com"
V_PULL_SECRET="registry-pull-secret"

# --- discovery -------------------------------------------------------------------------
#
# By glob, never by naming `service` literally: a chart added for another profile must be
# picked up automatically, because "uncovered" and "covered" have to be distinguishable
# without anyone remembering to edit this file. Matching on Chart.yaml rather than on the
# directory name `helm/` is the same argument taken one step further — it also finds
# templates/<profile>/chart/, templates/<profile>/deploy/helm/ and anything else that is
# genuinely a chart. Subcharts under charts/ are skipped: Helm renders them with their parent.
charts="$(find templates -type f -name Chart.yaml 2>/dev/null | grep -v '/charts/' | sed 's|/Chart\.yaml$||' | sort || true)"

echo
echo "== discovered scaffold charts =="
if [ -z "${charts}" ]; then
  printf '%s\n' "(none)"
  die "no chart found under templates/ (searched for **/Chart.yaml).
      Either the scaffolds lost their charts, or this discovery no longer matches the layout.
      Both mean the scaffold charts are UNSCANNED, and that is the failure this gate exists
      to make loud rather than silent."
fi
printf '%s\n' "${charts}"
n_charts="$(printf '%s\n' "${charts}" | wc -l | tr -d ' ')"

work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT

total_resources=0
total_passed=0
total_scans=0

while IFS= read -r chart; do
  [ -n "${chart}" ] || continue
  slug="$(printf '%s' "${chart#templates/}" | tr '/' '-')"

  echo
  echo "==================================================================="
  echo "== chart: ${chart}"
  echo "==================================================================="

  # --- substitute a throwaway copy -----------------------------------------------------
  # Same mechanism as standard/compose.sh: bash-native replacement rather than sed, because a
  # value may contain any character including the delimiters sed would need.
  src="${work}/${slug}/chart"
  mkdir -p "${src%/chart}"
  cp -R "${chart}" "${src}"

  while IFS= read -r f; do
    c="$(cat "${f}")"
    c="${c//@@PROJECT@@/${V_PROJECT}}"
    c="${c//@@PKG@@/${V_PKG}}"
    c="${c//@@PREFIX@@/${V_PREFIX}}"
    c="${c//@@GROUP@@/${V_GROUP}}"
    c="${c//@@DESCRIPTION@@/${V_DESCRIPTION}}"
    c="${c//@@REGISTRY@@/${V_REGISTRY}}"
    c="${c//@@PULL_SECRET@@/${V_PULL_SECRET}}"
    printf '%s\n' "${c}" > "${f}"
  done < <(find "${src}" -type f)

  # The generator's hard fail, applied to the scaffold: a token nobody taught this script is a
  # build error here, not a chart that renders with a literal `@@…@@` in a resource name.
  if grep -rn '@@' "${src}" >/dev/null 2>&1; then
    echo "leftover placeholders:"
    grep -rno '@@[A-Z_]*@@' "${src}" | sort -u -t: -k3 || true
    die "unsubstituted placeholder(s) remain in ${chart}.
      A scaffold token was added that this check does not know a value for. Teach it one here,
      the same way a new token has to be taught to standard/compose.sh in the same change —
      see docs/contracts.md, 'The @@…@@ placeholder vocabulary'."
  fi

  # --- which skip list applies ---------------------------------------------------------
  # The scaffold's own .checkov.yaml, because that is the list the repo spawned from this chart
  # will actually run. Copied beside the rendered manifest and picked up by checkov from the
  # working directory, so this gate and a spawned repo cannot disagree about what is waived.
  cfg=""
  d="$(dirname "${chart}")"
  while [ "${d}" != "." ] && [ "${d}" != "/" ]; do
    if [ -f "${d}/.checkov.yaml" ]; then cfg="${d}/.checkov.yaml"; break; fi
    d="$(dirname "${d}")"
  done
  [ -n "${cfg}" ] || cfg=".checkov.yaml"
  if [ -f "${cfg}" ]; then
    echo "skip list: ${cfg}"
  else
    echo "skip list: NONE FOUND — every check applies"
    cfg=""
  fi

  # --- render passes -------------------------------------------------------------------
  # Pass 1 is the chart's own defaults. Pass 2 is an optional overlay per chart, and it is not
  # decoration: the service chart's httproute.yaml, pdb.yaml and servicemonitor.yaml are all
  # behind `enabled: false`, so on defaults alone HALF THE CHART is never rendered by anything
  # in this repository — a check that looks complete and covers three of six templates is the
  # same defect one level down.
  overlay="auto-tests/group-a/scaffold-chart-values/${slug}.yaml"
  passes="defaults"
  [ -f "${overlay}" ] && passes="defaults all-features"

  for pass in ${passes}; do
    echo
    echo "-- pass: ${pass} --"
    rendered="${work}/${slug}-${pass}/rendered.yaml"
    mkdir -p "$(dirname "${rendered}")"

    helm_args=(template "${V_PROJECT}" "${src}")
    if [ "${pass}" = "all-features" ]; then
      helm_args+=(-f "${root}/${overlay}")
      echo "values overlay: ${overlay}"
    fi

    # FATAL, never a warning. A render this gate cannot complete is a chart nothing scanned.
    if ! helm "${helm_args[@]}" > "${rendered}" 2> "${rendered}.err"; then
      echo "helm stderr:"
      cat "${rendered}.err"
      die "helm template failed for ${chart} (pass: ${pass}).
      This is the failure checkov downgrades to a WARNING and then skips the chart over.
      Here it is fatal, on purpose."
    fi
    [ -s "${rendered}" ] || die "helm template produced an EMPTY manifest for ${chart} (pass: ${pass})"

    kinds="$(grep -c '^kind:' "${rendered}" || true)"
    echo "rendered ${kinds} resource(s):"
    grep '^kind:' "${rendered}" | sed 's/^/  /'
    [ "${kinds}" -gt 0 ] || die "helm template rendered no Kubernetes resource for ${chart} (pass: ${pass})"

    # --- scan --------------------------------------------------------------------------
    scan="${work}/${slug}-${pass}/scan"
    mkdir -p "${scan}"
    cp "${rendered}" "${scan}/rendered.yaml"
    [ -n "${cfg}" ] && cp "${root}/${cfg}" "${scan}/.checkov.yaml"

    out="${work}/${slug}-${pass}/checkov-json"
    rc=0
    ( cd "${scan}" && checkov -d . --framework kubernetes \
        -o cli -o json --output-file-path "console,${out}" ) || rc=$?

    # checkov writes the JSON either as the path given or as <path>/results_json.json,
    # depending on how the output list is interpreted. Accept both rather than pinning one.
    json="${out}"
    [ -d "${out}" ] && json="${out}/results_json.json"
    [ -f "${json}" ] || die "checkov produced no JSON result for ${chart} (pass: ${pass}) — the scan cannot be verified, so it did not happen"

    read -r passed failed skipped perrors resources < <(
      "${PY}" - "${json}" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
runs = d if isinstance(d, list) else [d]
t = {"passed": 0, "failed": 0, "skipped": 0, "parsing_errors": 0, "resource_count": 0}
for r in runs:
    s = r.get("summary") or {}
    for k in t:
        t[k] += int(s.get(k) or 0)
print(t["passed"], t["failed"], t["skipped"], t["parsing_errors"], t["resource_count"])
PYEOF
    )

    echo "checkov: resources=${resources} passed=${passed} failed=${failed} skipped=${skipped} parsing_errors=${perrors} (exit ${rc})"

    # THE GUARD THIS TICKET IS ABOUT. A scan that parsed nothing reports the same "0 failed"
    # as a scan that found nothing wrong, and a green pipeline cannot tell the two apart.
    [ "${resources}" -gt 0 ] || die "checkov parsed ZERO resources from ${chart} (pass: ${pass}).
      'checkov ran and found nothing' and 'checkov parsed nothing' must never look alike —
      that equivalence is the entire defect this gate closes."
    [ "${perrors}" -eq 0 ] || die "checkov reported ${perrors} parsing error(s) for ${chart} (pass: ${pass})"
    [ "${failed}" -eq 0 ]  || die "checkov reported ${failed} failed check(s) for ${chart} (pass: ${pass}) — see the findings above"
    [ "${rc}" -eq 0 ]      || die "checkov exited ${rc} for ${chart} (pass: ${pass})"

    total_resources=$((total_resources + resources))
    total_passed=$((total_passed + passed))
    total_scans=$((total_scans + 1))
  done
done <<EOF
${charts}
EOF

echo
echo "==================================================================="
echo "OK: ${n_charts} scaffold chart(s), ${total_scans} scan(s), ${total_resources} resource(s) parsed, ${total_passed} check(s) passed, 0 failed"
echo "==================================================================="
