#!/usr/bin/env bash
# Group-(a) functional smoke test. Chart linting lives in the shared `helm` CI job, so this
# script proves what only a running container can: that the image boots under the same
# restrictions the chart imposes, serves `/health` in the shape the profile mandates, and
# shuts down cleanly on SIGTERM.
#
# This is the script `templates/service/` scaffolds, with its placeholders resolved —
# deliberately. A reference implementation running a weaker test than the one it ships is how
# a defect survives in the scaffold: nobody exercises it here, so nobody finds it.
#
# Contract with the shared functional runner: exit 0 = pass, 77 = skip, anything else = fail.
set -euo pipefail
cd "$(dirname "$0")/../.."

CONTAINER="app-smoke-$$"
PORT="${APP_PORT:-8080}"

if ! command -v docker >/dev/null 2>&1; then
  echo "SKIP: docker is not available in this environment"
  exit 77
fi

# THE DinD RULE. Under GitLab CI the container started below runs inside the docker:dind
# SERVICE, so its published port lives in that service's network namespace: from the job
# container it is reachable at host `docker`, NEVER at localhost. Probing 127.0.0.1 works on
# a laptop and can never work in CI — a whole class of "works for me" failures.
#
# This script hardcoded `localhost` until it was first run on GitLab. The service started
# correctly — the log said `listening on http://0.0.0.0:8080` — and the probe still failed for
# 30 seconds, because the port was published somewhere the probe could not reach. The measured
# difference, from the shared runner's own notes: 127.0.0.1 -> connection refused,
# docker -> 200 OK.
if [ -n "${FUNCTIONAL_PROBE_HOST:-}" ]; then
  HOST="${FUNCTIONAL_PROBE_HOST}"
elif [ -n "${CI:-}" ]; then
  HOST="docker"
else
  HOST="127.0.0.1"
fi

# Prefer the image this pipeline actually built: testing a locally rebuilt one proves
# something about the Dockerfile, not about the artifact that will be deployed. The local
# build keeps the script usable on a developer machine.
if [ -n "${IMAGE_REF:-}" ]; then
  echo "== using the image built by this pipeline: ${IMAGE_REF} =="
  docker pull "${IMAGE_REF}"
  IMAGE="${IMAGE_REF}"
else
  echo "== no IMAGE_REF: building deploy/Dockerfile locally =="
  IMAGE="app:smoke"
  DOCKER_BUILDKIT=1 docker build -f deploy/Dockerfile -t "${IMAGE}" .
fi

# Capture rc, clean up, exit rc. A script that leaves containers behind poisons the next job
# on the same runner; one that cleans up but loses the exit code turns a failure green.
cleanup() {
  rc=$?
  docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
  exit "${rc}"
}
trap cleanup EXIT

echo "== boot under chart-equivalent restrictions =="
# --read-only, --tmpfs /tmp, --user and --cap-drop mirror the pod securityContext. If this
# fails, the chart would have failed in the cluster, where the feedback loop is far slower.
docker run -d --name "${CONTAINER}" \
  --read-only --tmpfs /tmp \
  --user 10000:10000 \
  --cap-drop ALL \
  -e APP_HOST=0.0.0.0 \
  -e APP_PORT=8080 \
  -p "${PORT}:8080" \
  "${IMAGE}" >/dev/null

echo "== probe http://${HOST}:${PORT}/health =="
body=""
for _ in $(seq 1 30); do
  if body="$(curl -fsS "http://${HOST}:${PORT}/health" 2>/dev/null)"; then
    break
  fi
  body=""
  sleep 1
done

# Logs first, assertions second: on failure the log tail is the diagnosis, and it must print
# even though the assertion below aborts the script.
echo "== container logs (tail) =="
docker logs "${CONTAINER}" 2>&1 | tail -20 || true

if [ -z "${body}" ]; then
  echo "FAIL: /health did not answer within 30s at http://${HOST}:${PORT}/health"
  exit 1
fi
echo "health body: ${body}"

# Shape, not exact text: the profile mandates at least these two keys, and pinning the whole
# body would make every added field a test failure.
case "${body}" in
  *'"status"'*) ;;
  *) echo "FAIL: /health body has no \"status\" key"; exit 1 ;;
esac
case "${body}" in
  *'"version"'*) ;;
  *) echo "FAIL: /health body has no \"version\" key"; exit 1 ;;
esac

echo "== graceful shutdown: SIGTERM must exit within the grace period =="
# `docker stop` sends SIGTERM and only SIGKILLs after -t seconds, which is what Kubernetes
# does with terminationGracePeriodSeconds. Exit 137 here means the process ignored SIGTERM and
# was killed — in-flight work would be lost on every rollout.
docker stop -t 30 "${CONTAINER}" >/dev/null

echo "OK: image boots read-only as non-root, serves /health, and stops on SIGTERM"
