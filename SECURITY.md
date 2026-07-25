# Security Policy

## Reporting a vulnerability

Please report suspected vulnerabilities **privately** — do not open a public issue.

- Preferred: GitHub **private vulnerability reporting** (Security → *Report a vulnerability*).
- Or email: `security@example.com` (replace with your contact).

Include a description, reproduction steps, affected versions, and impact. We aim to
acknowledge within a few business days.

## Handling secrets

No secrets are ever committed. Tokens, sessions, and keys are loaded from the environment or
ignored local files only, and are treated as full-access credentials. If you believe a
secret was exposed, rotate it immediately and report it.

## Automated checks

CI runs a security suite on every push/PR: `bandit`, `pip-audit`, `semgrep`, `checkov`,
`hadolint`, `trivy`, and GitHub CodeQL. Dependency updates are proposed by Dependabot. See
[`CLAUDE.md`](CLAUDE.md) § *Build, artifacts & CI* and § *Agent security working agreements*.
