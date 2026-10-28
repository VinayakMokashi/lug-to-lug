"""The ingest renames photos only when count, timing and camera all agree with the plan."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any

import pytest
from PIL import ExifTags, Image

from lugtolug_tools.ingest import Report, ingest
from lugtolug_tools.plan import read_plan
from lugtolug_tools.testing import Camera, Settings, block_rows, write_plan


def _run(
    tmp_path: Path, camera: Camera, rows: list[dict[str, str]] | None = None, **options: Any
) -> Report:
    plan = read_plan(write_plan(tmp_path / "plan.csv", rows or block_rows()))["S03"]
    return ingest(
        plan,
        camera.folder,
        work=tmp_path / "work",
        manifests=tmp_path / "data",
        private_manifests=tmp_path / "private",
        **options,
    )


def _manifest(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _start(camera: Camera) -> None:
    camera.shoot(99)  # the slate
    camera.wait(20)


def test_a_clean_block_is_ingested(tmp_path: Path, camera: Camera) -> None:
    camera.block()
    report = _run(tmp_path, camera)
    assert report.ok, report.render()
    assert (report.found, report.expected) == (13, 13)
    assert report.timed == report.planned == [1, 2, 2, 2, 2, 2, 2]

    copies = sorted((tmp_path / "work" / "S03").glob("*.jpg"))
    assert len(copies) == 12
    assert [c.stem for c in copies[:3]] == [
        "P01_S03_T20-DAY_01_W01_1",
        "P01_S03_T20-DAY_01_W01_2",
        "P01_S03_T20-DAY_02_W01_1",
    ]
    rows = _manifest(tmp_path / "data" / "S03.csv")
    assert [r["watch_id"] for r in rows[::2]] == ["W01", "W01", "W02", "W03", "W01", "W01"]
    assert [r["reseat"] for r in rows[::2]] == ["yes", "yes", "", "", "yes", "yes"]
    first = rows[0]
    assert first["sha256"] == hashlib.sha256(copies[0].read_bytes()).hexdigest()
    assert first["lens"] == "Pixel 9a back camera 4.53mm f/1.7"
    assert (first["focal_length_mm"], first["subject_distance_m"]) == ("4.53", "0.3")
    assert (first["width"], first["height"], first["turned_deg"]) == ("160", "120", "0")

    private = _manifest(tmp_path / "private" / "S03.csv")
    assert private[0]["role"] == "slate"
    assert private[0]["image_id"] == ""
    assert private[1]["original"].startswith("PXL_20261102_")
    assert private[1]["captured"] == "2026-11-02T10:30:21.323"

    originals = sorted(camera.folder.glob("*.jpg"))
    with Image.open(copies[0]) as copy, Image.open(originals[1]) as original:
        assert copy.tobytes() == original.tobytes()
        exif = copy.getexif()
        sub = exif.get_ifd(ExifTags.IFD.Exif)
        assert ExifTags.Base.DateTimeOriginal not in sub
        assert ExifTags.Base.SubjectDistance in sub
        assert not exif.get_ifd(ExifTags.IFD.GPSInfo)
        assert "xmp" not in copy.info


def test_an_extra_photo_stops_the_ingest(tmp_path: Path, camera: Camera) -> None:
    camera.block()
    camera.shoot(5)
    report = _run(tmp_path, camera)
    assert not report.ok
    assert "14 photos, but the plan expects 13" in report.errors[0]
    assert not (tmp_path / "work").exists()
    assert not (tmp_path / "data").exists()


def test_an_extra_and_a_missing_photo_do_not_cancel_out(tmp_path: Path, camera: Camera) -> None:
    # Placement 3 got a third photo and placement 4 only one: the count is right, but
    # matching in order would label a photo of one watch as another.
    _start(camera)
    for watch, shots in [(0, 2), (0, 2), (1, 3), (2, 1), (0, 2), (0, 2)]:
        camera.placement(watch, shots)
    report = _run(tmp_path, camera)
    assert report.found == report.expected == 13
    assert not report.ok
    assert (
        "timing and plan disagree from group 3: the plan expects 2 photo(s) of "
        "placement 3 (W02), but 3 were taken together" in report.errors[0]
    )


def test_the_corrected_plan_ingests(tmp_path: Path, camera: Camera) -> None:
    _start(camera)
    for watch, shots in [(0, 2), (0, 2), (1, 3), (2, 2), (0, 2), (0, 2)]:
        camera.placement(watch, shots)
    rows = block_rows()
    rows[2]["shots"] = "3"
    report = _run(tmp_path, camera, rows)
    assert report.ok, report.render()
    assert (tmp_path / "work" / "S03" / "P01_S03_T20-DAY_03_W02_3.jpg").exists()


def test_trust_order_accepts_a_pause_inside_a_placement(tmp_path: Path, camera: Camera) -> None:
    _start(camera)
    camera.placement(0)
    camera.shoot(0)
    camera.wait(12)  # a long pause between the two photos of placement 2
    camera.shoot(0)
    camera.wait(25)
    for watch in (1, 2, 0, 0):
        camera.placement(watch)
    assert not _run(tmp_path, camera, dry_run=True).ok
    report = _run(tmp_path, camera, trust_order=True)
    assert report.ok, report.render()
    assert any("--trust-order" in w for w in report.warnings)


def _with_odd_photo(camera: Camera, **odd: Any) -> Path:
    """A block whose third placement starts with one photo shot differently."""
    _start(camera)
    camera.placement(0)
    camera.placement(0)
    path = camera.shoot(1, **odd)
    camera.shoot(1)
    camera.wait(25)
    for watch in (2, 0, 0):
        camera.placement(watch)
    return path


@pytest.mark.parametrize(
    ("odd", "error"),
    [
        ({"settings": Settings(zoom=2.0)}, "zoomed in (2x)"),
        ({"settings": Settings(focal_mm=1.835)}, "but the session started with"),
        ({"settings": Settings(model="Pixel 8")}, "taken with Pixel 8"),
        ({"settings": Settings(distance_m=0.06)}, "in macro range"),
        ({"tags": ".NIGHT"}, "not a plain photo (NIGHT)"),
        ({"tags": ".RAW-01.COVER"}, "not a plain photo (RAW-01)"),
        ({"size": (120, 160)}, "the phone turned, or the ratio changed"),
        ({"turned": True}, "looks turned 180 degrees"),
    ],
)
def test_camera_problems_stop_the_ingest(
    tmp_path: Path, camera: Camera, odd: dict[str, Any], error: str
) -> None:
    _with_odd_photo(camera, **odd)
    report = _run(tmp_path, camera)
    assert not report.ok
    assert any(error in e for e in report.errors), report.render()
    assert len(report.errors) == 1, report.render()  # only the odd photo is blamed


def test_a_checked_turn_is_recorded(tmp_path: Path, camera: Camera) -> None:
    turned = _with_odd_photo(camera, turned=True)
    report = _run(tmp_path, camera, turned={turned.name: 180})
    assert report.ok, report.render()
    rows = _manifest(tmp_path / "data" / "S03.csv")
    assert [r["turned_deg"] for r in rows if r["seq"] == "3"] == ["180", "0"]


def test_a_turn_must_name_a_photo_and_a_quarter_turn(tmp_path: Path, camera: Camera) -> None:
    camera.block()
    name = sorted(camera.folder.glob("*.jpg"))[3].name
    report = _run(tmp_path, camera, turned={"PXL_nope.jpg": 180, name: 45})
    assert "--turned names PXL_nope.jpg, which isn't in the session" in report.errors
    assert f"--turned {name}=45: a turn is 90, 180 or 270" in report.errors


def test_a_location_is_removed_and_reported(tmp_path: Path, camera: Camera) -> None:
    _start(camera)
    for watch in (0, 0, 1, 2, 0, 0):
        camera.placement(watch, settings=Settings(located=True))
    report = _run(tmp_path, camera)
    assert report.ok, report.render()
    assert any("carry a location" in w for w in report.warnings)
    for copy in (tmp_path / "work" / "S03").glob("*.jpg"):
        with Image.open(copy) as image:
            assert not image.getexif().get_ifd(ExifTags.IFD.GPSInfo)


def test_the_plan_date_must_match_the_photos(tmp_path: Path, camera: Camera) -> None:
    camera.block()
    report = _run(tmp_path, camera, block_rows(day="2026-11-03"))
    assert any("the plan says 2026-11-03" in e for e in report.errors)


def test_an_unchosen_watch_stops_the_ingest(tmp_path: Path, camera: Camera) -> None:
    camera.block()
    report = _run(tmp_path, camera, block_rows(watches=("W??", "W02", "W03")))
    assert "the plan has no watch chosen for placements [1, 2, 5, 6]" in report.errors


def test_other_files_stop_the_ingest(tmp_path: Path, camera: Camera) -> None:
    camera.block()
    (camera.folder / "PXL_20261102_050000000.RAW-02.ORIGINAL.dng").write_bytes(b"raw")
    (camera.folder / "desktop.ini").write_text("[.ShellClassInfo]", encoding="utf-8")
    report = _run(tmp_path, camera)
    assert report.errors == ["files that aren't JPEGs: PXL_20261102_050000000.RAW-02.ORIGINAL.dng"]


def test_a_missing_folder_is_reported(tmp_path: Path, camera: Camera) -> None:
    camera.folder.rmdir()
    assert "no folder of photos" in _run(tmp_path, camera).errors[0]


def test_a_dry_run_writes_nothing(tmp_path: Path, camera: Camera) -> None:
    camera.block()
    report = _run(tmp_path, camera, dry_run=True)
    assert report.ok
    assert not (tmp_path / "work").exists()
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "private").exists()


def test_ingesting_again_changes_nothing_unless_replaced(tmp_path: Path, camera: Camera) -> None:
    camera.block()
    assert _run(tmp_path, camera).ok
    before = (tmp_path / "data" / "S03.csv").read_bytes()
    assert _run(tmp_path, camera).ok  # the same photos and plan: identical output
    assert (tmp_path / "data" / "S03.csv").read_bytes() == before

    rows = block_rows()
    rows[2]["watch_id"] = "W09"  # the plan was wrong about placement 3
    report = _run(tmp_path, camera, rows)
    assert any("differs; use --replace" in e for e in report.errors)
    assert _run(tmp_path, camera, rows, replace=True).ok
    names = {p.stem for p in (tmp_path / "work" / "S03").glob("*.jpg")}
    assert "P01_S03_T20-DAY_03_W09_1" in names
    assert "P01_S03_T20-DAY_03_W02_1" not in names
