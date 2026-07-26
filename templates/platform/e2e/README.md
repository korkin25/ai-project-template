# Tier (d) — cross-service end-to-end

**This directory exists because nowhere else can hold it.** Every other repo in the group
writes tier (d) as "lives in the platform repo, not here"; this is that repo. A test that needs
two services and a real environment has exactly one home, and if it is not written here it is
not written anywhere — it becomes a manual check somebody remembers to do until they do not.

The directory ships empty on purpose. Its README is the contract for what goes in it.

## What belongs here

A scenario that proves **two or more repos still agree**, exercised against a real environment:

- A message published by one service is consumed, processed and observable through another's
  API — the whole path, not each half.
- A schema change is compatible in both directions at once: the new producer and the old
  consumer, then the reverse. This is the check that makes "producer first, then consumers"
  safe, and it cannot exist in either repo alone.
- A shared store is written by one service and read by another with the meaning both expect.
- The delivery path itself: the version pinned in the bundle is the version the running
  service reports.

## What does not

| Not here | Where |
|---|---|
| Anything provable with one service | that service's own tier (a)/(b) |
| "Does the bundle render / validate" | tier (a), the CI pipeline |
| "Did the environment converge, with the right values" | [`../auto-tests/group-b/`](../auto-tests/group-b/) |
| "Is the cluster capable of hosting this at all" | `scripts/check-requirements.py` |

The line is that tier (d) tests **the agreement between repos**. A test that fails when only
one repo is broken belongs to that repo, where its failure names an owner immediately instead
of arriving as "the platform is red".

## Rules

- **Each test names the contract it exercises, and its owner**, in the file's header and in
  the tier-(d) table in [`../docs/tests.md`](../docs/tests.md). A failure must point at a repo.
  A red suite that nobody owns gets muted, and a muted suite is worse than an absent one:
  it still looks like coverage.
- **A real cluster, never a mock.** A local k3s is a legitimate target and is the default for
  development. Mocking the other service is how two repos stay green while disagreeing about
  the same field — which is the exact failure this tier exists to catch.
- **A contract change in any service repo updates the matching test here, in the same change
  set** — a separate MR in this repo, linked by the `@@PREFIX@@` id. Deferred, it becomes a
  test asserting a contract that no longer exists, and the next person deletes it rather than
  repairing it.
- **Exit contract: `0` pass, `77` skip, anything else fail.** Identical to the `auto-tests/`
  groups, so a scenario can move between them. A scenario whose prerequisites are missing
  exits `77` **and says which one** — it never exits `0`.
- **Clean up after yourself.** These run against a shared environment: use a unique prefix or
  namespace per run, and remove what you created even when the test fails. A test that leaves
  fixtures behind poisons the next run and eventually gets disabled.
- **Read-only towards anything you did not create.** The credential the CI job uses is scoped
  to one non-production environment for this reason. If a test needs to write outside its own
  fixtures, that is a problem with the test, not a reason to widen the token.

## Running them

```bash
# Locally, against whatever the current kubecontext points at.
kubectl config current-context        # look at it before you run anything
sh e2e/<scenario>.sh

# In CI: the `e2e` job, MANUAL, using a protected read/test-scoped E2E_KUBECONFIG.
```

The job is manual and `allow_failure: true` on purpose. E2E here is a **promotion gate, not a
merge gate**: the enforcement is that a promotion MR states which run was green in the source
environment. A blocking manual button gets clicked; a sentence in an MR gets read.

## Format

```sh
#!/bin/sh
# <what agreement this proves>
#
# Contract: <the topic / endpoint / table>, owned by <repo>, consumed by <repo>
# Requires: <environment, credentials, fixtures — each one checked below, exit 77 if missing>
set -eu
```

Record every run in `AUTOPILOT-LOG.md` under **Verified by**, with the real output, and update
the status in [`../docs/tests.md`](../docs/tests.md).
