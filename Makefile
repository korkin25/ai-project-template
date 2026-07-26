# Developer entry points. `make check` mirrors the CI gates locally.
.DEFAULT_GOAL := help
VENV := .venv
PY := $(VENV)/bin/python

.PHONY: help setup lint type test check build image chart version clean

# GitVersion image for `make version` — keep in sync with the CI's GitVersion.
GITVERSION_IMAGE ?= gittools/gitversion:6.3.0

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n", $$1, $$2}'

setup: ## Create a venv and install dev dependencies
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"

lint: ## Ruff lint
	$(VENV)/bin/ruff check .

type: ## Mypy type-check
	$(VENV)/bin/mypy

test: ## Run tests
	$(VENV)/bin/pytest

check: lint type test ## Lint + type-check + test (the core CI gate)

build: ## Build the wheel/sdist
	$(PY) -m build

image: ## Build the Docker image locally
	DOCKER_BUILDKIT=1 docker build -f deploy/Dockerfile -t app:local .

chart: ## Lint + template the Helm chart
	helm lint helm && helm template t helm >/dev/null

version: ## Print the GitVersion SemVer (via Docker, no local install)
	@docker run --rm -v "$(CURDIR):/repo" $(GITVERSION_IMAGE) /repo /showvariable SemVer

clean: ## Remove build/test caches
	rm -rf dist build .pytest_cache .mypy_cache .ruff_cache **/__pycache__
