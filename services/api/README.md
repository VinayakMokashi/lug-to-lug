# lugtolug-api

The FastAPI service behind the web app and the MCP server. It runs on Cloud Run and scales to zero.

| Endpoint | What | Since |
|---|---|---|
| `GET /health` | Liveness, with the service and core versions, the environment and the commit | Phase 0 |

Run it locally from the repository root:

```bash
uv run poe api          # http://localhost:8000/health and /docs
```

Settings come from environment variables: `ENVIRONMENT` (`local`, `staging` or `production`) and `GIT_SHA` (set by the deploy).
