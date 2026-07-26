# Group (c) — human-in-the-loop methodologies

Checks that need a human: a judgement about whether an environment is *right* rather than
merely reconciled, an acceptance decision, a drill whose value is that a person performed it.

The flagship exercises here are the **promotion drill** and the **rollback drill**. Both are
procedures this repo claims to support in one sentence each — "promotion is a copy of a
version", "rollback is `git revert`" — and a claim that has never been executed is a
hypothesis. The first time either is performed for real, it is during an incident.

The agent never marks these done itself: it writes the methodology, proposes it, and records
the human's result.

## Format

One Markdown file per methodology:

```markdown
# <what is being verified>

**Why a human.** <the access or the judgement that cannot be automated>
**Prerequisites.** <environment, credentials, a version that can be moved>
**Steps.** <numbered, each with the exact command — copy-pasteable, not paraphrased>
**Expected.** <what a pass looks like, as the exact state to read back>
**If it fails.** <what to capture: the command, its full output, the resource state>
```

## The methodologies worth maintaining

| Methodology | Cadence | Why |
|---|---|---|
| **Promotion drill** — move one version between environments through the real process | after any change to the process; at least quarterly | The step people skip is checking tier (d) in the source environment, and only a human notices they skipped it. |
| **Rollback drill** — revert a bundle bump and confirm the previous version returns, timed | after any change to the render or the tree layout | The recorded time is the number an incident decision is made against. Without it, "we can roll back" is a belief. |
| First deploy of a service into a shared environment | per service | Confirm the version the running service reports is the one that was pinned — the whole delivery path in one check. |
| Disaster recovery: rebuild an environment from this repo alone | at least yearly | The claim is that the tree plus the secret store is sufficient. Every step that needed knowledge held by one person is a defect fixed in the same session. |
| Contract crossing rehearsal — producer, consumers, tier-(d) update, in order | when the group's shape changes | Merge order (library → producer → consumer → bundle) is easy to state and easy to get wrong, and getting it wrong breaks the consumer for the duration. |

Record every run in `AUTOPILOT-LOG.md` under **Verified by**, with the actual output —
including the steps that turned out to be missing from the procedure, which are then fixed in
the same change. A drill that only produces a "passed" is a drill nobody learned anything
from.
