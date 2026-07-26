# `roles/` — locally authored roles

Roles written **in this repo** live here, one directory each. Third-party roles are *not*
vendored into this directory: they are pinned in [`requirements.yml`](requirements.yml) and
downloaded on demand (`.gitignore` keeps the downloads out of git), because a pinned line is
reviewable and 4 000 vendored lines are not.

## When to write a role instead of adding tasks to the playbook

A role is the unit that can be reused across environments, tested on its own, and reasoned
about in isolation. Add tasks straight to `playbooks/site.yml` only while there is exactly
one of them; the moment a second environment needs the same thing, it is a role.

## Shape

```
roles/<name>/
  defaults/main.yml   overridable variables, every one documented in docs/configuration.md
  tasks/main.yml      the work — idempotent, FQCN module names, every task named
  handlers/main.yml   restarts and reloads, so a change triggers exactly one restart
  templates/          .j2 files
  meta/main.yml       dependencies and supported platforms (ansible-lint requires it)
```

## Rules a role in this repo must satisfy

- **Idempotent.** The second run reports zero changed. Prefer a module over `command`/`shell`;
  where a shell is unavoidable, guard it with `creates:`/`removes:` or an honest
  `changed_when:` — a task that always reports "changed" makes every run's diff meaningless,
  which is the same as having no diff.
- **Reproducible from zero.** No dependence on state a previous run happened to leave behind.
- **Pinned.** Every package, image, chart and binary the role installs is referenced by an
  exact version, taken from a variable so the pin is visible in one place.
- **No secrets.** Credentials arrive from the environment or a secret store; a role never
  contains one, not even a "temporary" default.
- **Recovery documented.** Whatever this role installs, `docs/runbook.md` says how to
  recover it. That runbook is the real test of an infra repo — and it is exercised by
  following it, not by writing it.
