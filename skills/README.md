# skills

Agent **Skills** for this project, authored once in the portable
[Agent Skills](https://agentskills.io) `SKILL.md` format so any compatible runtime (Claude
Code, OpenCode, and others) reads them unchanged. Only *distribution* differs per agent; the
content stays portable.

## Authoring

Each skill is a directory with a `SKILL.md` whose YAML frontmatter uses the **standard core
fields only** (`name`, `description`) so it stays runtime-agnostic:

```markdown
---
name: my-skill
description: One tight sentence on WHAT it does, then the concrete TRIGGERS (user phrases /
  slash command) that should invoke it. The description is how the agent decides to use it —
  make it specific.
---

# my-skill

Body: the steps to perform, inputs/outputs, and hard guardrails ("never do X").
```

The `description` is the single most important field — it is what surfaces the skill to the
agent. Lead with the action, then the trigger phrases.

## Distribution

- **Claude Code** — ship as a plugin from the git marketplace in this repo (`.claude-plugin/`):
  `/plugin marketplace add <owner>/<repo>` then `/plugin install <plugin>@<marketplace>`.
- **OpenCode / other runtimes** — discover `~/.claude/skills/*/SKILL.md` and `.claude/skills/*`
  natively; drop or symlink these `skills/` dirs there.

Keep the frontmatter to `name` + `description`; avoid runtime-only fields so the files stay
portable.

See [example-skill/SKILL.md](example-skill/SKILL.md) for a starting point.
