import re

import lugtolug_core


def test_version_is_semantic() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", lugtolug_core.__version__)
