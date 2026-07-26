# @@PROJECT@@

@@DESCRIPTION@@

The **substrate** everything else in the platform assumes: machines, the cluster, its
cluster-wide components, and the CI runners. It follows the **infra** profile of the shared
standard (`standard/profiles/infra.md`). It contains no application code, builds no image and
publishes no package — its output is *applied configuration*.

| | |
|---|---|
| Provisioning | Ansible (`playbooks/`, `roles/`, `inventories/<env>/`) |
| Cluster prerequisites | `manifests/` — namespaces, cluster-scoped objects |
| Recovery procedures | [`docs/runbook.md`](docs/runbook.md) — the real test of this repo |
| Rules | [`CLAUDE.md`](CLAUDE.md) — generated from `standard/` |

> **CI lints and validates. It never applies.** Applying to a cluster requires explicit human
> approval, every time — approval to apply once is never approval to apply again. See the
> banner at the top of `.gitlab-ci.yml` for why a pipeline holding cluster-admin credentials
> is a worse risk than the manual step it saves.

## Features

> What this repo provides to everyone else. Engineering history belongs in
> [`CHANGELOG.md`](CHANGELOG.md), open work in [`TODO.md`](TODO.md).

- **A reproducible cluster.** The substrate can be rebuilt from zero on fresh machines by
  following `docs/runbook.md` — versions pinned exactly, nothing applied by hand.
- **Cluster capabilities other repos depend on**: namespaces with enforced Pod Security
  Admission, the registry pull secret, the Gateway, the storage class, the secrets operator
  and the GitOps controller. The full list is the contract in
  [`docs/contracts.md`](docs/contracts.md).
- **CI runners** (tag `job-agent-local`) that every other repo's pipeline runs on.

## Adopting this scaffold

1. Replace every placeholder: `@@PROJECT@@`, `@@PREFIX@@` (ticket prefix), `@@GROUP@@`
   (GitLab namespace), `@@DESCRIPTION@@`, `@@CI_TEMPLATES_REF@@` (the tag of
   `open_ci_cd/templates` to pin). `grep -rnE '@{2}' .` must come back empty.
2. Run `./standard/compose.sh` to generate `CLAUDE.md`, and commit it.
3. Rename `inventories/laptop-local/` to the real environment and fill in the hosts and the
   pinned versions.
4. Work through `docs/runbook.md` on a throwaway environment — following it is how you find
   out what it is missing.

**Chicken-and-egg note:** this repo registers the runner that its own pipeline is tagged for.
Before that runner exists, point the tags in `.gitlab-ci.yml` at a SaaS runner, bootstrap by
hand from the runbook, then switch them back.

## Layout

```
ansible.cfg                    committed defaults — "worked on my machine" cannot happen
playbooks/site.yml             provisions the substrate; idempotent, reproducible from zero
roles/                         locally authored roles + requirements.yml (exact versions)
collections/requirements.yml   Ansible collections, exact versions
inventories/<env>/             one directory per environment: hosts.yml + group_vars/
manifests/                     raw cluster prerequisites, validated by CI, applied by a human
docs/runbook.md                how to recover each component
auto-tests/group-b, group-c    plan/verify scenarios and human methodologies
standard/                      the shared rulebook's sources + this repo's identity
```

## Working here

```bash
# Lint exactly what CI lints.
yamllint .
ansible-lint --exclude .ansible --exclude .venv
ansible-playbook --syntax-check playbooks/site.yml

# PLAN. Always. Read the diff before proposing an apply.
ansible-playbook -i inventories/<env> playbooks/site.yml --check --diff
kubectl diff -f manifests/

# APPLY — a human step, approved every time, from a workstation. Never from CI.
```

## Non-negotiables

- **Idempotent** — the second run changes nothing.
- **Reproducible from zero** — an undocumented prerequisite is a defect.
- **Nothing applied by hand without committing it** — a `kubectl edit` is either reverted by
  the reconciler or survives as invisible drift.
- **Pinned versions everywhere** — `latest` is an outage waiting for a quiet week.
- **Credentials from the environment**, never from a committed file.
- **Destructive operations are proposed, never executed autonomously** — print the command,
  let a human run it. Backups first for anything holding data.
- **Verification is the state of the system** — "applied successfully" is not verification;
  `Ready`, `Running`, `online`, "no drift" are.
