# `.versions/` — written by CI, never by a human

This directory holds the **only interface between this repo and the platform repo**: the
version of what was published.

| File | Written by | Contents |
|---|---|---|
| `docker-image.env` | `/docker-build.yml` | `CI_REGISTRY_IMAGE`, `CI_REGISTRY_IMAGE_TAG`, `IMAGE_REF`, `IMAGE_DIGEST` |
| `helm-chart.env` | `/helm-package.yml` | `CHART_NAME`, `CHART_VERSION`, `APP_VERSION`, `HELM_OCI_URL` |

`/commit_changes.yml` commits them back to the branch with `[skip ci]` after a successful
publish, so the repository always states what it last released without anyone remembering to
write it down.

**Never hand-edit these files.** They are evidence, not configuration: an edited value
claims a release that never happened, and the next pipeline overwrites it anyway. The
invariant they record is

> chart version == image tag == `GitVersion_SemVer` — one commit, one version, everywhere.

Deploying is a separate act in the platform repo: bump `chartVersion` in the target
environment's `bundle.yaml` in a reviewed MR. That MR is the deployment; reverting it is the
rollback. Nothing in this repo touches a cluster.
