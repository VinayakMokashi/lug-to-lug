# Lug to Lug web app

Next.js (App Router) with TypeScript in strict mode, Tailwind CSS, ESLint and Prettier. It runs on Cloud Run as a standalone Node server.

| Route | What | Since |
|---|---|---|
| `/` | Landing page | Phase 0 |
| `/status` | Web and API status, probed at request time | Phase 0 |
| `/health` | Liveness check (JSON), for Cloud Run and the smoke test | Phase 0 |

## Develop

Node 24 (LTS) with pnpm through Corepack (`corepack enable pnpm`). From this folder:

```bash
pnpm install
pnpm dev                  # http://localhost:3000
pnpm check                # lint, typecheck, format check: what CI runs
pnpm build                # production build into .next/standalone
```

Environment variables, read at request time:

| Variable | Used by | Default |
|---|---|---|
| `API_URL` | `/status`, to reach the API | none (the status page says so) |
| `ENVIRONMENT` | `/status`, `/health` | `local` |
| `GIT_SHA` | `/status`, `/health` | `unknown` |

For the API, run `uv run poe api` from the repository root and set `API_URL=http://localhost:8000`.
