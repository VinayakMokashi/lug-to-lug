# ADR-0007: Tooling and workflow

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

One repository holds Python (the core library, the API, later the MCP server and the ML and evaluation code) and a TypeScript web app ([ADR-0004](0004-web-stack.md)). The tooling has to:

- give the same results on a Windows laptop and on Linux CI;
- be fast enough to run on every commit;
- stop the mistakes that are expensive to undo once pushed to a public repository: secrets, and photos of people ([ADR-0006](0006-data-consent-and-privacy.md)).

## Decision

| Area | Choice |
|---|---|
| Python packages | A **uv workspace** on Python 3.12 with one committed `uv.lock`. The members are `packages/core` and `services/api`; the MCP server and the ML and evaluation code join as they are built. The root holds the shared tooling and the dev dependencies. |
| Tasks | **poethepoet**: `uv run poe check` runs lint, types and tests, the same as CI. `uv run poe` lists the rest. |
| Lint and format | **ruff** for both, line length 100. |
| Types | **mypy in strict mode** for every Python package, with the Pydantic plugin. The plan requires it for `packages/core`; the API is held to the same bar while it is small. |
| Tests | **pytest**, with `--import-mode=importlib` so test files in different packages can share names. |
| Web | **Node 24 (LTS)** and **pnpm** through Corepack, pinned in `packageManager`. `apps/web` is its own pnpm project with its own lockfile; a pnpm workspace comes when a second JavaScript package does. TypeScript in strict mode plus `noUncheckedIndexedAccess`; ESLint with Next.js's Core Web Vitals and TypeScript rules; Prettier for formatting. `pnpm check` runs lint, types and the format check. |
| Hooks | **pre-commit**: whitespace, end-of-file and LF checks; YAML, TOML and JSON syntax; large files and private keys; ruff; a uv lock check; **gitleaks** for secrets; and a guard that rejects photos under `data/`. |
| Text files | LF everywhere, enforced by `.gitattributes` and `.editorconfig`. |
| Commits | [Conventional Commits](https://www.conventionalcommits.org/), one purpose each. |
| Branches | Phase 0 commits to `main` directly. From Phase 1, work goes on `phase-N/<topic>` branches, merges through a pull request once CI passes (rebase merge), and the branch is deleted. |

How to set up and run all of it: [runbooks/local-development.md](../runbooks/local-development.md).

## Consequences

- Two toolchains and two lockfiles (`uv.lock`, `apps/web/pnpm-lock.yaml`). CI runs each only when its files change.
- A contributor needs uv, Node 24 with Corepack, and pre-commit. Docker, the Google Cloud CLI and Terraform are only needed for deploys.
- The gitleaks hook is built by pre-commit, which downloads a Go toolchain on its first run.
- The secret scan and the photo guard run before a commit exists, so neither depends on remembering a manual check.

## Alternatives considered

- **Poetry or pip-tools:** slower, and neither handles several packages under one lockfile as directly as a uv workspace.
- **Black, isort and flake8:** ruff covers all three and is much faster.
- **npm or Yarn:** pnpm is faster and refuses undeclared dependencies.
- **A pnpm workspace, Turborepo or Nx now:** nothing to coordinate while there is one JavaScript package.
- **Husky with lint-staged:** JavaScript-only; pre-commit covers both languages and the secret scan in one place.
- **Biome instead of ESLint and Prettier:** one fast tool, but Next.js ships its lint rules for ESLint.
