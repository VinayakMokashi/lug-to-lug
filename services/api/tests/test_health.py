import pytest
from fastapi.testclient import TestClient

import lugtolug_core
from lugtolug_api.main import create_app
from lugtolug_api.settings import Settings


def test_health_reports_versions_and_deploy() -> None:
    client = TestClient(create_app(Settings(environment="staging", git_sha="abc1234")))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "api",
        "version": "0.1.0",
        "core_version": lugtolug_core.__version__,
        "environment": "staging",
        "git_sha": "abc1234",
    }


def test_settings_read_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("GIT_SHA", "def5678")

    assert Settings.from_env() == Settings(environment="production", git_sha="def5678")


def test_settings_reject_an_unknown_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "prod")

    with pytest.raises(ValueError, match="ENVIRONMENT must be one of"):
        Settings.from_env()
