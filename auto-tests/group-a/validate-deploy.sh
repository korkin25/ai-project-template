#!/usr/bin/env bash
# Group-(a) functional smoke test. Chart linting lives in the shared `helm` CI job, so this
# script only proves the IMAGE actually boots and serves:
#   - docker build of the image
#   - boot the service and probe /health
# Contract (open-ci-actions functional runner): exit 0 = pass, 77 = skip, other = fail.
set -euo pipefail
cd "$(dirname "$0")/../.."

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not available — skipping functional smoke test"
  exit 77
fi

PORT="${APP_PORT:-8080}"

echo "== docker build =="
DOCKER_BUILDKIT=1 docker build -t app:ci-test .

echo "== boot service and probe /health on :${PORT} =="
docker rm -f app-ci >/dev/null 2>&1 || true
docker run -d --name app-ci -p "${PORT}:8080" app:ci-test >/dev/null
ok=0
for _ in $(seq 1 20); do
  if curl -fsS "localhost:${PORT}/health" >/dev/null 2>&1; then ok=1; break; fi
  sleep 1
done
docker logs app-ci | tail -10 || true
docker rm -f app-ci >/dev/null 2>&1 || true
test "$ok" = "1"

echo "OK: image boots and serves /health on :${PORT}"
