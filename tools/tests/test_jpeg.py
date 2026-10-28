"""Stripping metadata never changes a pixel, and removes everything it should."""

from __future__ import annotations

import io
from datetime import datetime

import pytest
from PIL import ExifTags, Image

from lugtolug_tools.jpeg import JpegError, scan, segments, strip_metadata
from lugtolug_tools.testing import Settings, exif_block, jpeg, scene

WHEN = datetime(2026, 11, 2, 10, 30, 0, 456000)


def _pixels(data: bytes) -> bytes:
    with Image.open(io.BytesIO(data)) as image:
        return image.tobytes()


def _minimal_exif() -> bytes:
    exif = Image.Exif()
    exif[ExifTags.Base.Model] = "Pixel 9a"
    return exif.tobytes()


@pytest.mark.filterwarnings("ignore:Image appears to be a malformed MPO file")
@pytest.mark.parametrize("progressive", [False, True])
@pytest.mark.parametrize("gain_map", [False, True])
def test_the_pixels_are_unchanged(progressive: bool, gain_map: bool) -> None:
    original = jpeg(
        scene(3, (320, 240)), exif_block(WHEN), gain_map=gain_map, progressive=progressive
    )
    stripped = strip_metadata(original, _minimal_exif())
    assert _pixels(stripped) == _pixels(original)
    assert len(stripped) < len(original)


def test_restart_markers_inside_the_scan_are_kept() -> None:
    buffer = io.BytesIO()
    scene(1, (320, 240)).save(buffer, "JPEG", quality=85, restart_marker_blocks=2)
    original = buffer.getvalue()
    assert b"\xff\xd0" in original
    assert _pixels(strip_metadata(original)) == _pixels(original)


def test_metadata_is_removed_and_the_colour_profile_kept() -> None:
    original = jpeg(scene(), exif_block(WHEN, Settings(located=True)), gain_map=True)
    stripped = strip_metadata(original, _minimal_exif())
    with Image.open(io.BytesIO(stripped)) as image:
        exif = image.getexif()
        assert "xmp" not in image.info
        assert "icc_profile" in image.info
        assert getattr(image, "n_frames", 1) == 1
    assert dict(exif) == {ExifTags.Base.Model: "Pixel 9a"}
    assert not exif.get_ifd(ExifTags.IFD.GPSInfo)
    found, end = scan(stripped)
    assert end == len(stripped)  # nothing after the image
    assert not any(s.marker == 0xE2 and s.payload.startswith(b"MPF") for s in found)


def test_no_exif_at_all() -> None:
    stripped = strip_metadata(jpeg(scene(), exif_block(WHEN)))
    assert all(s.marker != 0xE1 for s in segments(stripped))
    with Image.open(io.BytesIO(stripped)) as image:
        assert not image.getexif()


def test_comments_and_other_app_segments_are_dropped() -> None:
    original = jpeg(scene(), exif_block(WHEN))
    comment = b"\xff\xfe\x00\x07hello"
    app5 = b"\xff\xe5\x00\x06abcd"
    stripped = strip_metadata(original[:2] + comment + app5 + original[2:])
    assert b"hello" not in stripped
    assert all(s.marker not in (0xFE, 0xE5) for s in segments(stripped))


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"GIF89a", "not a JPEG"),
        (b"\xff\xd8\xff\xdb\x00\x43", "runs past the end"),
        (b"\xff\xd8\x00\x00", "expected a marker"),
        (b"\xff\xd8\xff\xd8", "second start-of-image"),
        (b"\xff\xd8", "ends before"),
    ],
)
def test_broken_files_are_refused(data: bytes, message: str) -> None:
    with pytest.raises(JpegError, match=message):
        strip_metadata(data)


def test_truncated_scan_data_is_refused() -> None:
    original = jpeg(scene(), exif_block(WHEN), xmp=False, icc=False)
    with pytest.raises(JpegError, match="scan data runs past the end"):
        strip_metadata(original[: len(original) // 2])


def test_the_exif_block_must_be_complete() -> None:
    with pytest.raises(ValueError, match="must start with"):
        strip_metadata(jpeg(scene()), b"MM\x00*")
