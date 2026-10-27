"""FastAPI application factory and the module-level app that uvicorn serves."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

import lugtolug_core
from lugtolug_api import __version__
from lugtolug_api.settings import Environment, Settings


class Health(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    core_version: str
    environment: Environment
    git_sha: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(
        title="Lug to Lug API",
        version=__version__,
        description="True-to-scale watch try-on: measure, try on, fit, search.",
    )

    @app.get("/health", tags=["ops"])
    def health() -> Health:
        """Liveness check for Cloud Run, the smoke test and the web app's status page."""
        return Health(
            status="ok",
            service="api",
            version=__version__,
            core_version=lugtolug_core.__version__,
            environment=settings.environment,
            git_sha=settings.git_sha,
        )

    return app


app = create_app()
