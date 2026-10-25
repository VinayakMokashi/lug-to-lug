# ADR-0002: Keep the documentation in the repository

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

The build runs over many sessions. It needs a record of what was done, why each choice was made and what was measured, versioned and reviewed together with the code.

## Decision

Everything lives in `docs/`:

| Path | Contents |
|---|---|
| `PLAN.md` | The living plan: definition of done, phases and steps, budget, risks, change log and status tracker |
| `BUILD_LOG.md` | One entry per working session: what changed, commands, results, problems, next steps |
| `decisions/` | Decision records, numbered and indexed in [README.md](README.md) |
| `concepts/` | One guide per component, explaining the idea behind it |
| `eval/` | Every measured result, with the command and data version that produced it |
| `cards/` | Data cards and model cards |
| `runbooks/` | Deploy, roll back, rotate secrets, delete a person's data |
| `site/` | The project page, published with GitHub Pages |

Decision records use the sections Status, Date, Context, Decision, Consequences and Alternatives considered. An accepted record is not rewritten: a later record supersedes it, and only its status line changes.

## Consequences

- A pull request that changes behaviour also updates the documents it affects.
- The plan's change log records every change to scope or method, with the reason.

## Alternatives considered

- **A wiki or an external notes tool:** not versioned with the code, and easy to let drift.
