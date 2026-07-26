# Autopilot log — @@PROJECT@@

**This file is the resume point.** A session can end at any moment; the next one — a
different agent, or a human — must be able to read this and continue without re-deriving
anything. Newest entry first, one `##` section per working session.

Write an entry for any autonomous change of substance: a bundle change, a schema or renderer
change, a contract crossing coordinated from here, a decision taken, or a blocker discovered.
A trivial typo fix does not need one.

**Rules that make this useful rather than decorative:**

- **Facts, not intentions.** *Verified by* carries a real result — the command and what it
  printed, or the CI job id. In this repo that means the read-back from the environment, not
  the merge: merging starts the reconcile, and a reconcile can fail.
- **Every entry is reversible.** Here the reverse is almost always "revert MR !n", and saying
  so is not a formality — it is the check that the change really was one MR, in one repo,
  affecting one environment. If you cannot describe the undo in a sentence, the change was
  too large to have been made autonomously.
- **A blocker that was found and not fixed still gets an entry.** A version that cannot be
  promoted because a consumer has not moved is exactly the kind of thing the next session will
  otherwise rediscover from a failing pipeline.
- **Cross-repo work names every repo it touched**, with each local ticket id. This log is the
  only place the whole crossing is visible; each participating repo only ever sees its half.
- **Append-only.** Correct a wrong entry with a new one that says so; never rewrite history.

Format:

```markdown
## YYYY-MM-DD — <short title>

**What changed.** <the actual change, concretely — environment, component, from → to version>
**Why.** <the reason, including what was rejected and why, if a choice was made>
**Verified by.** <the command or CI run that proves it works, with its result>
**Reverse.** <how to undo it — usually `git revert` of a named MR>
**Open.** <anything left unfinished or blocked, with the ticket id>
```

---

_No entries yet — the first autonomous change adds one above this line._
