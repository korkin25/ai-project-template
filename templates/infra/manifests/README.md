# `manifests/` — raw cluster prerequisites

Kubernetes objects that must exist **before** anything else can be installed, and that are
too small or too foundational to justify a chart: namespaces, cluster-scoped RBAC, storage
classes, priority classes, the GitOps controller's sync root.

CI validates every file here (`validate_manifests` in `.gitlab-ci.yml`) and **never applies
any of them**. Applying is a human step, and it is documented in
[`../docs/runbook.md`](../docs/runbook.md).

## What does *not* belong here

- **Any application, and any application's version.** That is the platform repo's bundle. An
  infra repo that pins an application version has taken over a job it cannot do consistently
  — it would need to know which versions are compatible with each other in each environment,
  which is exactly what the platform repo exists to know.
- **Any chart.** A component with a chart is installed from that chart at a pinned version,
  not by a copy of its rendered output. A committed render is a second source of truth and
  guarantees drift.
- **Anything holding a secret value.** Manifests here are public within the group. Secrets
  are seeded through the documented bootstrap procedure (`../docs/configuration.md`) and
  thereafter managed by the secrets operator.

## Conventions

- One file per concern, named after what it creates (`namespaces.yaml`, `storageclass.yaml`).
- Multiple documents in one file are fine when they are one concern; unrelated objects sharing
  a file makes a targeted rollback impossible.
- Every object is namespaced or explicitly cluster-scoped — never relying on the caller's
  current context, which is how an object lands in `default` on someone's laptop.
- Every image, chart or operator referenced is pinned to an exact version. `latest` in an
  infra repo is an outage waiting for a quiet week.
