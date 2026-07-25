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
