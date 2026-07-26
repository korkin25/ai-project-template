---
name: data-plane-version-audit
description: Audit and plan upgrades for DATA SERVICES — the database, message bus, vector store and cache that hold state. Use monthly, or when asked to check whether the data plane is up to date, plan a database or broker upgrade, or review changelogs for stateful components. NOT for cluster substrate like the CNI, cert-manager or operators — those have their own skill (cluster-version-audit).
---

# Data plane version audit

Same cadence as the cluster audit, deliberately a different skill — because the question is
different. For the substrate you ask *"will the cluster survive this"*. Here you ask
**"will the data survive this, and can I get back if it does not"**.

**Scope:** the database, the message bus, the vector store, the cache, the CDC connector.
Anything holding state that outlives its pod. The CNI, cert-manager, operators and GitOps
controllers belong to `cluster-version-audit`.

## The one rule that makes this skill different

**A stateful upgrade is frequently one-way.** Postgres rewrites its data directory; a broker
rewrites its log format; a vector store rewrites its index. After that the previous version
often cannot read what the new one wrote — so "roll back the chart version" restores the
binary and not the data.

Therefore: **the backup is step one, not step three**, and an upgrade whose restore path has
not been *exercised* is not planned, it is hoped.

## Report, then stop

This produces a plan. Applying it touches data and requires explicit human approval, with a
window, every time.

## Steps

### 1. Establish the before-picture

Run this **from the root of the repository that owns the pins** — the infra or platform repo
whose manifests declare them — not from wherever this skill was installed. The version reader
ships with that repo, at `scripts/check-versions.py` — the `infra` scaffold provides one, and
any other repo holding pins is expected to provide its own at the same path. It reads pins out
of the manifest tree, so run anywhere else it writes an empty `before.json`, and an empty
before-picture is worse than none: it gets attached to the log as evidence.

```bash
./scripts/check-versions.py --json > /tmp/before.json
kubectl -n <ns> get cluster,helmrelease,statefulset,pvc
```

**If that repo has no `scripts/check-versions.py`, do not skip the step and do not write one
mid-audit.** Record the pins by hand into `/tmp/before.json`, and state in the report that it
was assembled manually — the file is quoted later as the thing the after-picture is compared
against, so how it was produced is part of what it means.

Then capture what the numbers must still say afterwards — row counts, topic offsets,
collection sizes. An upgrade that silently drops data looks identical to one that did not,
unless you wrote the number down first.

### 2. Prove the restore path, before planning anything

For every component holding state, answer with a command and its real output:

- Where is the last backup, and **when** was it actually taken?
- Has a restore from it ever been performed? If never, the backup is a belief.
- How long does the restore take? That number is the length of the maintenance window.

If a component has no exercised restore path, **that is one of the most valuable lines in the
report** — state it plainly and keep analysing that component anyway. A first restore
attempted under pressure, after a failed upgrade, is the worst possible time to discover the
backup was incomplete; that is an argument for saying so loudly, not for leaving the
component out. The user decides what to do with the risk; your job is that they can see it.

### 3. Classify by data risk, not by SemVer distance

| Component | What the version bump actually is |
|---|---|
| **PostgreSQL major** | not a tag change — a data-directory rewrite. Under an operator it has a documented procedure (offline `pg_upgrade`, or replica-and-switchover). Read the operator's docs, not the database's |
| **PostgreSQL minor** | usually a restart; still check the release notes for a required `REINDEX` |
| **Message bus** | log-format and inter-broker protocol version. Consumer offsets and consumer-group state must survive; a downgrade after the format bumps is not possible |
| **CDC connector** | replication slots and publications. A slot that is dropped and recreated **loses everything since its last confirmed LSN** — this is the quietest data-loss path in the whole platform |
| **Vector store** | on-disk index format. Collections may need rebuilding, which for a large corpus is hours of embedding, not minutes of restart |
| **Cache** | persistence file format (AOF/RDB). Usually safe to lose — but confirm nothing has quietly started treating it as a store of record |

### 4. Read the changelogs, looking for different things than the cluster audit

- **Data format or storage engine changes**, and whether they are automatic and irreversible.
- **Required intermediate versions.** Stateful software far more often refuses to skip.
- **Deprecated settings that are now removed** — the pod starts, ignores the setting, and
  behaves differently. For this platform, `wal_level=logical` and the replication-slot
  settings are load-bearing: without them there is no CDC at all.
- **Client/protocol compatibility**: which client versions the new server still accepts. The
  services pin their own client libraries independently, so the server can move out from
  under them.

### 5. Write the plan

```
<component>  <pinned> -> <target>
  data risk:   what state can be lost or rewritten
  backup:      command, where it lands, verified restore time
  procedure:   the operator's documented steps, in order — not "bump the tag"
  verify:      the data assertions from step 1, re-run
  rollback:    what actually restores service, and whether it costs the data written since
               the backup. If the answer is "restore and lose N minutes", say N. If there is
               no path back, write `NONE FOUND` and what you checked — an absent rollback is
               a finding to surface, never a reason to drop the entry.
  recommendation: what you would do, marked as advice. The decision is the user's.
```

Sequence across components matters: upgrade the **producer side before the consumer** where a
protocol changes, and never upgrade the database and its CDC connector in the same window —
if the slots break you want to know which change did it.

### 6. Hand it over

Record the plan, add an `AUTOPILOT-LOG.md` entry with `/tmp/before.json` attached, and report:

- **every** component that moved, in full — ordered by data risk rather than by version
  distance, but never trimmed to the ones you would act on;
- which upgrades could be batched and which want a window of their own, as advice;
- **explicitly, which components have no exercised restore path** — usually the most valuable
  line in the report and the one most likely to be skipped.

Hand over the complete analysis. Deciding what to upgrade, and what risk is acceptable, is
the user's call — and they can only make it against everything you found.

## Guardrails

- **Never apply.** No chart upgrade, no `kubectl apply`, no operator CR edit against a live
  cluster.
- **Never take a backup as a side effect of auditing.** A backup is a deliberate act with a
  known destination and a known retention, not a step buried inside a read-only check.
- **A major version of a stateful component is never "just a bump".** If a plan for one reads
  like a tag change, the operator's documentation has not been read.
- **Never filter the report.** Rank and annotate; omit nothing. A component you judged too
  risky to touch still gets its full entry — that judgement is exactly what the user needs to
  see in order to disagree with it.
- **Say the size.** "Rebuilding the index takes hours" is planning; "may take a while" is not.
- **Report unknowns as unknown.** A version you could not resolve is a finding, not a blank.
- **Never write the audit tool during the audit.** If the repo ships no version checker, read
  the pins by hand and say so. A checker written under time pressure and never verified is
  the worst kind of verifier: it is believed, and it arrives carrying the report's authority.
