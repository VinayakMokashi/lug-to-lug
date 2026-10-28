"""What the tools read from a camera JPEG: when it was taken, by which camera and lens.

Only the metadata the benchmark needs survives ingest (see `kept_exif`): the camera
model, the orientation tag, and the lens, zoom, focus and exposure values that
calibration and the quality checks use. Capture times are read here to order and group
the photos, then dropped.

Facts about Pixel 9a files this relies on (checked on published full-size samples):
pixels are stored already rotated with orientation tag 1; 1x photos from the main
camera are 4000 x 3000 with a 4.53 mm focal length; 2x zoom keeps the focal length and
image size and only changes DigitalZoomRatio; SubjectDistance holds the focus distance
in metres; and a GPS block with only a compass heading can be present without any
location.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from PIL import ExifTags, Image
from PIL.TiffImagePlugin import IFDRational

# Pixel Camera names photos PXL_<UTC date>_<UTC time to the millisecond>, followed by
# dotted tags when a special mode was used: .NIGHT, .PORTRAIT-01.COVER, .MP (a motion
# photo), .RAW-01.COVER (with a DNG beside it), .MOTION-01.COVER.
PIXEL_NAME = re.compile(r"^PXL_(?P<day>\d{8})_(?P<time>\d{9})(?P<tags>(?:\.[A-Z0-9-]+)*)", re.I)
DEVIATION_TAGS = frozenset({"NIGHT", "PORTRAIT", "MP", "RAW", "MOTION"})

_TAG = ExifTags.Base
_GPS = ExifTags.GPS
_GPS_IFD = ExifTags.IFD.GPSInfo
_EXIF_IFD = ExifTags.IFD.Exif
_INFINITY = 4294967295  # how SubjectDistance writes "focused at infinity"


@dataclass(frozen=True)
class Photo:
    path: Path
    sha256: str
    width: int  # as stored; Pixel phones store pixels already rotated
    height: int
    orientation: int
    captured: datetime | None  # local time, to the millisecond
    make: str
    model: str
    lens: str
    focal_length_mm: float | None
    focal_length_35mm: int | None
    digital_zoom: float | None  # 0 or 1 when not zoomed
    subject_distance_m: float | None  # the focus distance
    f_number: float | None
    exposure_s: float | None
    iso: int | None
    has_location: bool  # a latitude or longitude, not just a compass heading
    has_heading: bool  # a compass heading, which Pixel phones write without a location
    name_tags: tuple[str, ...]

    @property
    def deviations(self) -> list[str]:
        """Pixel name tags showing the photo wasn't a plain photo."""
        return [t for t in self.name_tags if t.upper().split("-")[0] in DEVIATION_TAGS]

    @property
    def zoomed(self) -> bool:
        return self.digital_zoom is not None and self.digital_zoom > 1.0


def _number(value: object) -> float | None:
    if isinstance(value, IFDRational | int | float):
        number = float(value)
        return number if number == number else None  # a 0/0 rational reads as NaN
    return None


def _captured(sub: dict[int, object]) -> datetime | None:
    text = sub.get(_TAG.DateTimeOriginal)
    if not isinstance(text, str):
        return None
    try:
        when = datetime.strptime(text.strip(), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    subsec = sub.get(_TAG.SubsecTimeOriginal)
    if isinstance(subsec, str) and subsec.strip().isdigit():
        when += timedelta(microseconds=int(subsec.strip().ljust(6, "0")[:6]))
    return when


def read_photo(path: Path) -> Photo:
    data = path.read_bytes()
    with Image.open(path) as image:
        if image.format != "JPEG":
            raise ValueError(f"{path.name} is not a JPEG")
        width, height = image.size
        exif = image.getexif()
        sub = dict(exif.get_ifd(_EXIF_IFD))
        gps = exif.get_ifd(_GPS_IFD)
    match = PIXEL_NAME.match(path.stem)
    tags = tuple(t for t in match["tags"].split(".") if t) if match else ()
    f35 = sub.get(_TAG.FocalLengthIn35mmFilm)
    iso = sub.get(_TAG.ISOSpeedRatings)
    orientation = exif.get(_TAG.Orientation, 1)
    distance = _number(sub.get(_TAG.SubjectDistance))
    return Photo(
        path=path,
        sha256=hashlib.sha256(data).hexdigest(),
        width=width,
        height=height,
        orientation=orientation if isinstance(orientation, int) else 1,
        captured=_captured(sub),
        make=str(exif.get(_TAG.Make, "")).strip("\x00 "),
        model=str(exif.get(_TAG.Model, "")).strip("\x00 "),
        lens=str(sub.get(_TAG.LensModel, "")).strip("\x00 "),
        focal_length_mm=_number(sub.get(_TAG.FocalLength)),
        focal_length_35mm=f35 if isinstance(f35, int) else None,
        digital_zoom=_number(sub.get(_TAG.DigitalZoomRatio)),
        subject_distance_m=None if distance in (None, float(_INFINITY)) else distance,
        f_number=_number(sub.get(_TAG.FNumber)),
        exposure_s=_number(sub.get(_TAG.ExposureTime)),
        iso=iso if isinstance(iso, int) else None,
        has_location=_GPS.GPSLatitude in gps or _GPS.GPSLongitude in gps,
        has_heading=_GPS.GPSImgDirection in gps,
        name_tags=tags,
    )


# The only tags a benchmark copy keeps, copied exactly as the camera wrote them.
KEPT_TAGS = (_TAG.Make, _TAG.Model, _TAG.Orientation)
KEPT_EXIF_TAGS = (
    _TAG.LensModel,
    _TAG.FocalLength,
    _TAG.FocalLengthIn35mmFilm,
    _TAG.DigitalZoomRatio,
    _TAG.SubjectDistance,
    _TAG.FNumber,
    _TAG.ExposureTime,
    _TAG.ISOSpeedRatings,
)


def kept_exif(path: Path) -> bytes:
    """The EXIF block a benchmark copy carries: no times, no location, no maker notes."""
    with Image.open(path) as image:
        width, height = image.size
        original = image.getexif()
        original_sub = original.get_ifd(_EXIF_IFD)
    exif = Image.Exif()
    for tag in KEPT_TAGS:
        if tag in original:
            exif[tag] = original[tag]
    sub = exif.get_ifd(_EXIF_IFD)
    for tag in KEPT_EXIF_TAGS:
        if tag in original_sub:
            sub[tag] = original_sub[tag]
    sub[_TAG.ExifImageWidth] = width
    sub[_TAG.ExifImageHeight] = height
    return exif.tobytes()
