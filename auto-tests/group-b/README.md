# group-b — dev-machine / AI-sandbox scenarios

Tests that can only run on a developer machine or against external services, or that can't be
fully automated. The agent runs these during development and again after a release once full
CI is green. Add one Markdown methodology or script per scenario, e.g. a `kind-deploy.md`
that installs the Helm chart on a local cluster and asserts readiness + `/health`.
