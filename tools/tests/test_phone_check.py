"""phone-check turns the settings sheet's open questions into answers from real files."""

from __future__ import annotations

from typing import Any

import pytest

from lugtolug_tools.phone_check import Check, check_phone, run
from lugtolug_tools.photos import read_photo
from lugtolug_tools.testing import SIZE, Camera, Settings

FAKE_FRAME = frozenset({SIZE, SIZE[::-1]})


def _series(camera: Camera, n: int = 12, **odd: Any) -> list[Check]:
    """The sheet's test: a series with the remote, focus and exposure locked."""
    for i in range(n):
        camera.shoot(i % 3, **(odd if i == n - 1 else {}))
        camera.wait(2)
    photos = [read_photo(p) for p in sorted(camera.folder.glob("*.jpg"))]
    return check_phone(photos, frame=FAKE_FRAME)


def _status(checks: list[Check]) -> dict[str, str]:
    return {c.name: c.status for c in checks}


def test_a_good_series_passes(camera: Camera) -> None:
    checks = _series(camera)
    status = _status(checks)
    assert "FAIL" not in status.values(), checks
    assert status["focus and exposure lock held"] == "PASS"
    assert status["Ultra HDR off"] == "PASS"
    assert status["sRGB colour"] == "PASS"
    info = {c.name: c.detail for c in checks}
    assert info["compass heading"] == "12 of 12 files carry one (removed at ingest)"
    assert info["timing"].startswith("12 photos over")


@pytest.mark.filterwarnings("ignore:Image appears to be a malformed MPO file")
@pytest.mark.parametrize(
    ("odd", "check"),
    [
        ({"settings": Settings(zoom=2.0)}, "1x zoom"),
        ({"settings": Settings(focal_mm=1.835)}, "main lens"),
        ({"settings": Settings(model="Pixel 8")}, "camera"),
        ({"settings": Settings(located=True)}, "location off"),
        ({"settings": Settings(distance_m=0.05)}, "not macro"),
        ({"gain_map": True}, "Ultra HDR off"),
        ({"tags": ".MP"}, "plain photo mode"),
        ({"size": (120, 160)}, "same way up"),
        ({"size": (200, 120)}, "full 4:3 frame"),
        ({"turned": True}, "not upside down"),
    ],
)
def test_each_setting_that_is_wrong_fails(camera: Camera, odd: dict[str, Any], check: str) -> None:
    assert _status(_series(camera, **odd))[check] == "FAIL"


def test_a_lock_that_did_not_hold_is_reported(camera: Camera) -> None:
    checks = _series(camera, settings=Settings(exposure_denominator=60, distance_m=0.34))
    lock = next(c for c in checks if c.name == "focus and exposure lock held")
    assert lock.status == "INFO"
    assert "the lock did not hold" in lock.detail


def test_raw_and_video_files_are_listed(camera: Camera) -> None:
    camera.shoot()
    (camera.folder / "PXL_20261102_050000000.RAW-02.ORIGINAL.dng").write_bytes(b"raw")
    _, others = run(camera.folder)
    assert others == ["PXL_20261102_050000000.RAW-02.ORIGINAL.dng"]


def test_an_empty_folder_fails(camera: Camera) -> None:
    assert check_phone([]) == [Check("photos", "FAIL", "no JPEGs found")]
