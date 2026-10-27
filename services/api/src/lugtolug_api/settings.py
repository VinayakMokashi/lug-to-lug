"""Runtime settings, read once from the environment."""

import os
from dataclasses import dataclass
from typing import Literal

Environment = Literal["local", "staging", "production"]
_ENVIRONMENTS: tuple[Environment, ...] = ("local", "staging", "production")


@dataclass(frozen=True, slots=True)
class Settings:
    environment: Environment = "local"
    git_sha: str = "unknown"

    @classmethod
    def from_env(cls) -> "Settings":
        environment = os.environ.get("ENVIRONMENT", "local")
        if environment not in _ENVIRONMENTS:
            msg = f"ENVIRONMENT must be one of {_ENVIRONMENTS}, got {environment!r}"
            raise ValueError(msg)
        return cls(
            environment=environment,
            git_sha=os.environ.get("GIT_SHA", "unknown"),
        )
