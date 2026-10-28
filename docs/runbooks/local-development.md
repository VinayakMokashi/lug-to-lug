# Local development

How to set up the repository and run what CI runs. The choices behind the tools are in [ADR-0007](../decisions/0007-tooling-and-workflow.md).

## Tools

| Tool | Version | For |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | 0.12 | Python 3.12 (uv installs it if missing), the workspace and the tasks |
| [Node.js](https://nodejs.org/) | 24 LTS | The web app; Corepack ships with it |
| pnpm | pinned in `apps/web/package.json` | The web app's packages, through Corepack |
| [pre-commit](https://pre-commit.com/) | 4 | Hooks on every commit: `uv tool install pre-commit` |
| Docker | any recent | Building the container images |
| Google Cloud CLI, Terraform | current | Deploys and infrastructure only |

## First time

```bash
git clone https://github.com/VinayakMokashi/lug-to-lug.git
cd lug-to-lug
uv sync                       # Python packages and dev tools into .venv
pre-commit install            # hooks run on every commit from now on
corepack enable pnpm
pnpm -C apps/web install
```

## Every day

| Command (from the repository root) | What |
|---|---|
| `uv run poe check` | Python: ruff, mypy (strict), pytest |
| `uv run poe fmt` | Python: fix lint findings and format |
| `pnpm -C apps/web check` | Web: ESLint, TypeScript, Prettier check |
| `pnpm -C apps/web format` | Web: format |
| `uv run poe contracts` and `pnpm -C apps/web contracts` | Regenerate the Python and TypeScript contracts after changing a schema in `data/schemas` ([ADR-0009](../decisions/0009-catalogue-and-stand-in-specification.md)); CI fails if they are stale |
| `pre-commit run --all-files` | Every hook on every file, including the secret scan |
| `uv run poe api` | The API on http://localhost:8000 (`/health`, `/docs`) |
| `pnpm -C apps/web dev` | The web app on http://localhost:3000 |

To see the web app talk to the API locally, start both and give the web app the API's address: `API_URL=http://localhost:8000 pnpm -C apps/web dev`, then open `/status`.

## Rules the hooks enforce

- No secrets: gitleaks scans every commit. Keys live in `.env` (ignored) locally and in Secret Manager in the cloud.
- No photos under `data/`: they stay in the private photo store ([ADR-0006](../decisions/0006-data-consent-and-privacy.md)).
- LF line endings and a final newline in every text file.
- `uv.lock` matches the `pyproject.toml` files.
