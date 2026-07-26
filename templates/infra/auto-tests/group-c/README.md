# Group (c) — human-in-the-loop methodologies

For this repo the flagship tier-(c) exercise is **following
[`../../docs/runbook.md`](../../docs/runbook.md) end to end**. That runbook is the real test
of an infra repo, and it is exercised by following it — not by writing it. A procedure nobody
has ever run is a hypothesis, and it is discovered to be wrong at the worst possible moment.

The agent never marks these done itself: it writes the methodology, proposes it, and records
the human's result.

## Format

```markdown
# <what is being verified>

**Why a human.** <the access or the judgement that cannot be automated>
**Prerequisites.** <environment, credentials, a machine that can be destroyed>
**Steps.** <numbered, each with the exact command — copy-pasteable, not paraphrased>
**Expected.** <what a pass looks like, as the exact state to read back>
**If it fails.** <what to capture: the command, its full output, the resource state>
```

## The methodologies worth maintaining

| Methodology | Cadence | Why |
|---|---|---|
| Rebuild from zero, following the runbook verbatim | after any structural change; at least yearly | Proves reproducibility, which is the property that turns a lost machine from a disaster into an afternoon. |
| Recover each component from the runbook | once per component, then after any change to it | A recovery procedure is only credible once someone other than its author has followed it. |
| Runner recovery, without using CI | after any change to the runner | Circular dependency: the runner is what CI needs in order to fix anything, including itself. It must be recoverable by hand. |
| Restore from backup | before it is needed | A backup that has never been restored is not a backup. |
| Credential rotation | on staff change, and on schedule | The procedure is only correct if it has been executed; a rotation that half-works locks everyone out of the cluster. |

Record every run in `AUTOPILOT-LOG.md` under **Verified by**, with the actual output —
including the steps that turned out to be missing from the runbook, which are then fixed in
the same change.
