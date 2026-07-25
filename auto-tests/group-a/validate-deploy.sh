#!/usr/bin/env bash
# Group-(a) deploy artifacts smoke test. Runs in CI and locally:
#   - helm lint + template (default and toggled values)
#   - docker build of the image
#   - boot the service and probe /health
# Fails on the first error.
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "== helm lint =="
helm lint chart

echo "== helm template (default + toggles) =="
helm template t chart >/dev/null
helm template t chart \
  --set gatewayApi.enabled=true --set 'gatewayApi.parentRefs[0].name=gw' \
  --set persistence.enabled=true \
  --set serviceMonitor.enabled=true \
  --set podDisruptionBudget.enabled=true >/dev/null

echo "== docker build =="
DOCKER_BUILDKIT=1 docker build -t app:ci-test .

echo "== boot service and probe /health =="
docker run -d --name app-ci -p 8080:8080 app:ci-test >/dev/null
ok=0
for _ in $(seq 1 20); do
  if curl -fsS localhost:8080/health >/dev/null 2>&1; then ok=1; break; fi
  sleep 1
done
docker logs app-ci | tail -10 || true
docker rm -f app-ci >/dev/null 2>&1 || true
test "$ok" = "1"

echo "OK: deploy artifacts validated"
