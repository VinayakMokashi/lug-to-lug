from pathlib import Path

import pytest

from lugtolug_tools import paths


def test_the_defaults_sit_next_to_the_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LUGTOLUG_PRIVATE_DIR", raising=False)
    monkeypatch.delenv("LUGTOLUG_WORK_DIR", raising=False)
    assert (paths.REPO / "pyproject.toml").is_file()
    assert paths.private_dir() == paths.REPO.parent / "private"
    assert paths.work_dir() == paths.REPO.parent / "work"
    assert paths.data_dir() == paths.REPO / "data"


def test_the_environment_overrides_them(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LUGTOLUG_PRIVATE_DIR", str(tmp_path / "store"))
    monkeypatch.setenv("LUGTOLUG_WORK_DIR", str(tmp_path / "scratch"))
    assert paths.private_dir() == tmp_path / "store"
    assert paths.work_dir() == tmp_path / "scratch"
