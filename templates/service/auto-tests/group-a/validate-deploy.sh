#!/usr/bin/env bash
# Tier-(a) functional smoke test for @@PROJECT@@ — run by /functional.yml on every pipeline.
#
# CONTRACT (functional.yml is the caller; this is its public API):
#   exit 0  = passed
#   exit 77 = skipped — a prerequisite is missing. Used, not "fail", so a fork or an
#             unconfigured clone stays green instead of teaching everyone to ignore red.
#   other   = failed
#   cwd     = repository root, stdin = /dev/null, IMAGE_REF exported when this pipeline
#             built an image.
#
# WHAT IT PROVES, and why each part is here rather than in a unit test:
#   1. the image BOOTS as built — no missing dependency, no bad entrypoint;
#   2. it boots under the same restrictions the chart imposes (read-only root filesystem,
#      non-root uid 10001, /tmp as the only writable mount). A service that only works with
#      a writable rootfs passes every unit test and then CrashLoops in the cluster;
#   3. GET /health answers 200 with {"status", "version"} — the runtime contract the chart's
#      probes and the platform's tier-(d) tests depend on;
#   4. SIGTERM shuts it down gracefully with exit code 0 within the grace period. This is
#      the check nothing else can make: a service that ignores SIGTERM looks perfectly
#      healthy until a rollout drops its in-flight work.
#
# Chart linting is NOT here: helm-package.yml already renders and packages the chart.
set -euo pipefail
cd "$(dirname "$0")/../.."

CONTAINER="@@PROJECT@@-smoke-$$"
PORT="${APP_PORT:-8080}"

if ! command -v docker >/dev/null 2>&1; then
  echo "SKIP: docker is not available in this environment"
  exit 77
fi

# THE DinD RULE. Under GitLab CI the container started below runs inside the docker:dind
# SERVICE, so its published port lives in that service's network namespace: from the job
# container it is reachable at host `docker`, NEVER at localhost. Probing 127.0.0.1 works on
# a laptop and can never work in CI — a whole class of "works for me" failures.
if [ -n "${FUNCTIONAL_PROBE_HOST:-}" ]; then
  HOST="${FUNCTIONAL_PROBE_HOST}"
elif [ -n "${CI:-}" ]; then
  HOST="docker"
else
  HOST="127.0.0.1"
fi

# Prefer the image this pipeline actually built and pushed: testing a locally rebuilt image
# proves something about the Dockerfile, not about the artifact that will be deployed.
# Falling back to a local build keeps the script usable on a developer machine.
if [ -n "${IMAGE_REF:-}" ]; then
  echo "== using the image built by this pipeline: ${IMAGE_REF} =="
  docker pull "${IMAGE_REF}"
  IMAGE="${IMAGE_REF}"
else
  echo "== no IMAGE_REF: building deploy/Dockerfile locally =="
  IMAGE="@@PROJECT@@:smoke"
  DOCKER_BUILDKIT=1 docker build -f deploy/Dockerfile -t "${IMAGE}" .
fi

# Capture rc, clean up, exit rc — a script that leaves containers behind poisons the next
# job on the same runner, and one that cleans up but loses the exit code turns a failure
# green. The trap covers every exit path including `set -e`.
cleanup() {
  rc=$?
  docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
  exit "${rc}"
}
trap cleanup EXIT

echo "== boot under chart-equivalent restrictions =="
# --read-only + --tmpfs /tmp + --user 10001 mirror the pod securityContext exactly. If this
# fails, the chart would have failed in the cluster, where the feedback loop is far slower.
docker run -d --name "${CONTAINER}" \
  --read-only --tmpfs /tmp \
  --user 10001:10001 \
  --cap-drop ALL \
  -e APP_PORT=8080 \
  -e APP_VERSION=smoke-test \
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

# Logs first, assertions second: on failure the log tail is the diagnosis, and it must be
# printed even though the assertion below aborts the script.
echo "== container logs (tail) =="
docker logs "${CONTAINER}" 2>&1 | tail -20 || true

if [ -z "${body}" ]; then
  echo "FAIL: /health did not answer within 30s"
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

echo "== graceful shutdown: SIGTERM must exit 0 within the grace period =="
# `docker stop` sends SIGTERM and only SIGKILLs after -t seconds, which is exactly what
# Kubernetes does with terminationGracePeriodSeconds. Exit code 137 here means the process
# ignored SIGTERM and was killed — i.e. in-flight work would be lost on every rollout.
docker stop -t 30 "${CONTAINER}" >/dev/null
exit_code="$(docker inspect -f '{{.State.ExitCode}}' "${CONTAINER}")"
if [ "${exit_code}" != "0" ]; then
  echo "FAIL: container exited ${exit_code} after SIGTERM (137 = SIGKILL: the signal was ignored)"
  exit 1
fi

echo "OK: image boots read-only as uid 10001, serves /health, and stops gracefully"
