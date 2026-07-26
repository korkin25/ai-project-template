# Group (c) — human-in-the-loop methodologies

Checks that need a human: a visual review, a judgement about a real environment, an
acceptance decision. The agent never marks these done itself — it **writes the methodology
here and proposes it to the user**.

A methodology is a document, not a script. It is useful precisely because it can say
"look at whether the dashboard makes sense", which no assertion can express.

## Format

One Markdown file per methodology:

```markdown
# <what is being verified>

**Why a human.** <the judgement that cannot be automated>
**Prerequisites.** <environment, access, data>
**Steps.** <numbered, each with the exact command or click>
**Expected.** <what a pass looks like, concretely>
**If it fails.** <what to capture: logs, screenshots, ids — so the report is actionable>
```

## Suggested methodologies for this service

- First deploy into a shared environment: follow the platform repo's bundle bump, then read
  back pod status, logs and `/health` — and confirm the version reported there is the one
  that was released.
- Rollback drill: revert the bundle MR and confirm the previous version returns, with the
  time it took recorded.
