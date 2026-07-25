# Autopilot log — ai-project-template

Autonomous changes (user authorized publishing this repo + full autopilot on the CI chain).

## 2026-07-26 — adopt open-ci-actions + publish

- **CI is now a composition of `korkin25/open-ci-actions@v1`** (detect → version → python /
  sast / docker / helm / functional / release), replacing the inline jobs. `.github/workflows/ci.yml`
  is the canonical reference composition (copy-paste for new projects). CodeQL + doc-sync stay
  as bespoke extra workflows. _Reverse:_ restore the previous inline `ci.yml` from git history.
- **Functional script slimmed** to image boot + `/health` probe (chart lint is the shared
  `helm` job now). Contract exit 0/77/other.
- **Published as a PUBLIC repo, default branch `dev`** (branch model feature/* → dev → rc →
  release; no main). This is the reference implementation every other project is aligned to.
- Docs kept in lockstep (CLAUDE.md Build/CI section, README, CHANGELOG).

## 2026-07-26 — CI debugging (open-ci-actions v1.0.2)

- **Removed `.github/workflows/codeql.yml`.** On a fresh public repo GitHub auto-enables
  CodeQL *default setup*, which conflicts with an advanced CodeQL workflow → 0s
  startup_failure ("workflow file issue"). CodeQL still runs via GitHub's default setup
  (Security → Code scanning), no workflow file needed. If a bespoke CodeQL config is wanted
  later, add it to open-ci-actions' `sast.yml`, not as a per-repo workflow. Docs updated.
- **Upstream fix in open-ci-actions v1.0.2:** checkov's SARIF `--output-file-path` must name
  a file, not a directory (checkov 3.x IsADirectoryError → no report → hard fail). Fixed in
  `sast.yml`; this repo picks it up via `@v1`.
- Pipeline result before these fixes: 15/16 green (checkov the only failure) + functional
  (script-driven) green — proving the composition works end to end on the demo app.
