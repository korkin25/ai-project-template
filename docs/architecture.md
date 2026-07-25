# Architecture

> **Design-before-code lives here.** Per `CLAUDE.md`, no implementation starts until the
> design for a task is written down (data model, public API/contract, deployment shape,
> trade-offs vs. alternatives) and any architectural decision is approved. Record each such
> design in this file (or the ticket) before coding.

## Overview

<Describe what the system is and its main components in a few sentences.>

## Components

| Component | Responsibility |
|-----------|----------------|
| `src/app/` | <the service> |
| … | … |

## Data model

<The source of record, storage, schema, and what is derived/rebuildable.>

## Public interfaces / contracts

<CLI commands, HTTP/MCP API surface, event formats — the things other systems depend on.>

## Deployment shape

Container image (GHCR) → Helm chart (`chart/`). See `chart/README.md`. Runtime configuration
is in [configuration.md](configuration.md).

## Decisions log

Record architectural decisions as `PRJ-D<n>` (short ADR-style entries): context → options →
decision → consequences.

- _PRJ-D1 — … (template: replace)._
