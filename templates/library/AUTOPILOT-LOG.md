# Autopilot log — @@PROJECT@@

**This file is the resume point.** A session can end at any moment; the next one — a
different agent, or a human — must be able to read this and continue without re-deriving
anything. Newest entry first, one `##` section per working session.

Write an entry for any autonomous change of substance: a feature, a refactor, a CI change, a
decision taken, or a blocker discovered. A trivial typo fix does not need one.

**Rules that make this useful rather than decorative:**

- **Facts, not intentions.** *Verified by* carries a real result — the command and what it
  printed, or the CI job id. If something was not verified, write that instead of implying
  it was.
- **Every entry is reversible.** If you cannot describe how to undo a change, that is a
  signal the change was too large to have been made autonomously in the first place.
- **A blocker that was found and not fixed still gets an entry.** A known blocker nobody
  wrote down costs the next session an hour.
- **Append-only.** Correct a wrong entry with a new one that says so; never rewrite history.

Format:

```markdown
## YYYY-MM-DD — <short title>

**What changed.** <the actual change, concretely — files, behaviour, versions>
**Why.** <the reason, including what was rejected and why, if a choice was made>
**Verified by.** <the command or CI run that proves it works, with its result>
**Reverse.** <how to undo it — a revert, a config flip, a restored file>
**Open.** <anything left unfinished or blocked, with the ticket id>
```

---

_No entries yet — the first autonomous change adds one above this line._
