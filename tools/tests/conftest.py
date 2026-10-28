from datetime import datetime
from pathlib import Path

import pytest

from lugtolug_tools.testing import Camera


@pytest.fixture
def camera(tmp_path: Path) -> Camera:
    return Camera(tmp_path / "raw" / "S03", datetime(2026, 11, 2, 10, 30, 0, 123000))
