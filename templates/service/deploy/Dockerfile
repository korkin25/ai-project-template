# syntax=docker/dockerfile:1.7
# Image for @@PROJECT@@ -> @@REGISTRY@@/@@GROUP@@/@@PROJECT@@
#
# Path is deploy/Dockerfile because that is the shared templates' DOCKERFILE default
# (globals.yml); keeping it there means .gitlab-ci.yml needs no override.
#
# Two stages on purpose: the builder holds pip, wheels, build backends and the credentials
# used to reach the group index; the runtime holds a finished virtualenv and nothing else.
# A single-stage image ships the package manager and the build cache to production, which is
# both a larger attack surface and a slower pull on every node.
#
# The runtime image is designed to run with a READ-ONLY root filesystem (the chart sets
# readOnlyRootFilesystem: true and mounts an emptyDir at /tmp). Nothing here writes outside
# /tmp: bytecode writing is off, pip is absent, HOME points at /tmp.

# ---------------------------------------------------------------------------------------
# Builder — resolves and installs dependencies into a self-contained virtualenv
# ---------------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /src

# pyproject.toml and src/ are copied together because the build backend reads the package
# out of src/ while building the wheel; copying only the manifest first would fail the
# build, not save a layer.
#
# README.md is a BUILD INPUT, not documentation, because pyproject.toml declares
# `readme = "README.md"`: hatchling resolves it while generating metadata and the build dies
# with "Readme file does not exist: README.md" if it is absent. Verified by removing this
# line — the failure is at metadata generation, and its message never mentions the Dockerfile.
COPY README.md ./
COPY pyproject.toml ./
COPY src/ ./src/

# The pip_index secret carries the authenticated GitLab PyPI URL, so group-internal packages
# resolve without the token ever entering an image layer or `docker history`. CI maps it via
# DOCKERBUILD_SECRET_pip_index=PIP_EXTRA_INDEX_URL (see .gitlab-ci.yml).
#
# --extra-index-url is added ONLY when the secret exists AND is non-empty: a bare
# `--extra-index-url` with an empty value swallows the following `.` argument and pip dies
# with "You must give at least one requirement to install". The `|| true` on `cat` covers a
# local `docker build` with no secret mounted at all.
RUN --mount=type=secret,id=pip_index \
    EXTRA=""; \
    URL="$(cat /run/secrets/pip_index 2>/dev/null || true)"; \
    [ -n "$URL" ] && EXTRA="--extra-index-url $URL"; \
    python -m venv /opt/venv; \
    /opt/venv/bin/pip install --no-cache-dir $EXTRA .

# ---------------------------------------------------------------------------------------
# Runtime — the published image
# ---------------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# HOME=/tmp keeps any library that insists on a home directory (caches, .config) writable
# under a read-only rootfs, where /tmp is the only mounted emptyDir.
# PYTHONUNBUFFERED makes logs appear in `kubectl logs` immediately instead of when a 4 KiB
# buffer happens to fill — a buffered crash log is a lost crash log.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    HOME=/tmp \
    APP_HOST=0.0.0.0 \
    APP_PORT=8080

# A dedicated uid/gid, high and fixed. High because checkov CKV_DOCKER_3 / CKV_K8S_40 reject
# low uids that can collide with host system accounts; fixed because the chart pins
# runAsUser/runAsGroup to the same numbers and the two must not drift apart.
# --no-create-home: there is no writable home under a read-only rootfs; HOME=/tmp covers it.
RUN groupadd --gid 10001 app \
 && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv

# Numeric so Kubernetes can verify runAsNonRoot without resolving /etc/passwd (a name-only
# USER makes the kubelet fail the pod with "container has runAsNonRoot and image has
# non-numeric user").
USER 10001:10001

EXPOSE 8080

# Liveness signal for `docker run` and for checkov CKV_DOCKER_2. Kubernetes ignores it and
# uses the chart's probes instead, but it is what makes a locally started container
# self-reporting. urllib rather than curl: the runtime image has no shell utilities beyond
# the interpreter, and adding curl for a health check is a package (and a CVE feed) too many.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('APP_PORT','8080'), timeout=3).status == 200 else 1)"]

# Exec form (no shell): PID 1 is the interpreter itself, so SIGTERM from Kubernetes reaches
# the process directly. Wrapped in a shell it would be swallowed and every pod deletion
# would end in a SIGKILL after terminationGracePeriodSeconds — i.e. in-flight work lost and
# offsets uncommitted, which is precisely what src/@@PKG@@/main.py takes care to avoid.
CMD ["python", "-m", "@@PKG@@.main"]
