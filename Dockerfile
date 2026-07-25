# syntax=docker/dockerfile:1
#
# Multi-stage image for the sample app. Built and pushed to GHCR by CI. The default
# command serves the HTTP service on :8080; replace with your real entry point.

ARG PYTHON_VERSION=3.12

# ---- build: produce a wheel and a self-contained venv -----------------------
FROM python:${PYTHON_VERSION}-slim AS build
# EXTRAS optionally selects extra optional-dependencies groups, e.g. --build-arg EXTRAS=foo.
ARG EXTRAS=""
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src
RUN python -m pip install --upgrade pip build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m build --wheel --outdir /dist \
 && python -m venv /opt/venv \
 && if [ -n "$EXTRAS" ]; then \
      /opt/venv/bin/pip install "$(echo /dist/*.whl)[${EXTRAS}]"; \
    else \
      /opt/venv/bin/pip install /dist/*.whl; \
    fi

# ---- final: slim runtime, non-root ------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS final
LABEL org.opencontainers.image.description="ai-project-template sample service" \
      org.opencontainers.image.licenses="MIT"

# uid/gid 10000 matches the chart's securityContext (runAsNonRoot). Pre-create the
# data dir owned by the app user so bare `docker run` and docker named volumes
# (which inherit the mountpoint's ownership) are writable; in k8s the PVC mounts over it.
RUN groupadd -g 10000 app \
 && useradd -u 10000 -g 10000 -m -d /home/app -s /usr/sbin/nologin app \
 && mkdir -p /data \
 && chown 10000:10000 /data

COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/app \
    APP_HOST=0.0.0.0 \
    APP_PORT=8080

WORKDIR /app
USER 10000
EXPOSE 8080

# Default: serve the HTTP service. Override CMD for your CLI/other entry points.
ENTRYPOINT ["app-serve"]
