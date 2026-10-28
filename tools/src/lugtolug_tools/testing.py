"""A fake Pixel 9a for tests: small JPEGs with the metadata a real one writes.

Real files are 4000 x 3000; these are 160 x 120 so the tests stay fast. The scene is a
grey backdrop with a forearm across it and a watch whose dial shade changes with each
placement, so consecutive photos are nearly identical, as on the rig. The metadata
follows real Pixel 9a files: local capture time to the millisecond, the lens and zoom
tags, the focus distance, a GPS block holding only a compass heading, an sRGB profile
and XMP, and optionally an HDR gain map after the image.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from PIL import ExifTags, Image, ImageCms, ImageDraw
from PIL.TiffImagePlugin import IFDRational

from lugtolug_tools.plan import COLUMNS

_TAG = ExifTags.Base
_GPS = ExifTags.GPS
SIZE = (160, 120)
OFFSET = timedelta(hours=5, minutes=30)  # file names are UTC, EXIF times local
SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
XMP = b"<x:xmpmeta xmlns:x='adobe:ns:meta/'>hdrgm</x:xmpmeta>"


def scene(watch: int = 0, size: tuple[int, int] = SIZE) -> Image.Image:
    w, h = size
    image = Image.new("RGB", size, (128, 128, 128))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, w * 0.08, h), fill=(60, 60, 70))  # the book that stops the elbow
    draw.rectangle((0, h * 0.35, w * 0.8, h * 0.65), fill=(198, 150, 120))  # the forearm
    draw.ellipse((w * 0.78, h * 0.3, w * 0.98, h * 0.7), fill=(190, 140, 110))  # the hand
    shade = (40 + 37 * watch) % 220
    draw.ellipse((w * 0.4, h * 0.38, w * 0.52, h * 0.62), fill=(shade, shade, 200))  # the watch
    return image


@dataclass(frozen=True)
class Settings:
    """What the fake camera writes into each photo's EXIF."""

    model: str = "Pixel 9a"
    focal_mm: float = 4.53
    zoom: float = 0.0
    distance_m: float = 0.3
    exposure_denominator: int = 120
    iso: int = 100
    located: bool = False


DEFAULT = Settings()


def exif_block(when: datetime, settings: Settings = DEFAULT) -> bytes:
    exif = Image.Exif()
    exif[_TAG.Make] = "Google"
    exif[_TAG.Model] = settings.model
    exif[_TAG.Orientation] = 1
    exif[_TAG.Software] = "HDR+ 1.0.748116481zd"
    sub = exif.get_ifd(ExifTags.IFD.Exif)
    sub[_TAG.DateTimeOriginal] = when.strftime("%Y:%m:%d %H:%M:%S")
    sub[_TAG.SubsecTimeOriginal] = f"{when.microsecond // 1000:03d}"
    sub[_TAG.OffsetTimeOriginal] = "+05:30"
    sub[_TAG.LensModel] = f"Pixel 9a back camera {settings.focal_mm}mm f/1.7"
    sub[_TAG.FocalLength] = IFDRational(round(settings.focal_mm * 1000), 1000)
    sub[_TAG.FocalLengthIn35mmFilm] = 24
    sub[_TAG.DigitalZoomRatio] = IFDRational(round(settings.zoom * 100), 100)
    sub[_TAG.SubjectDistance] = IFDRational(round(settings.distance_m * 1000), 1000)
    sub[_TAG.FNumber] = IFDRational(17, 10)
    sub[_TAG.ExposureTime] = IFDRational(1, settings.exposure_denominator)
    sub[_TAG.ISOSpeedRatings] = settings.iso
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps[_GPS.GPSVersionID] = b"\x02\x02\x00\x00"
    gps[_GPS.GPSImgDirectionRef] = "M"
    gps[_GPS.GPSImgDirection] = IFDRational(50, 1)
    if settings.located:
        gps[_GPS.GPSLatitudeRef] = "N"
        gps[_GPS.GPSLatitude] = (IFDRational(18, 1), IFDRational(31, 1), IFDRational(0, 1))
        gps[_GPS.GPSLongitudeRef] = "E"
        gps[_GPS.GPSLongitude] = (IFDRational(73, 1), IFDRational(51, 1), IFDRational(0, 1))
    return exif.tobytes()


def jpeg(
    image: Image.Image,
    exif: bytes | None = None,
    *,
    gain_map: bool = False,
    progressive: bool = False,
    icc: bool = True,
    xmp: bool = True,
) -> bytes:
    """Encode like the phone: EXIF, XMP and an sRGB profile, and optionally a gain map."""
    buffer = io.BytesIO()
    image.save(
        buffer,
        "JPEG",
        quality=90,
        progressive=progressive,
        exif=exif or b"",
        icc_profile=SRGB if icc else None,
        xmp=XMP if xmp else b"",
    )
    data = buffer.getvalue()
    if gain_map:
        small = io.BytesIO()
        Image.new("L", (40, 30), 200).save(small, "JPEG")
        mpf = b"MPF\x00" + b"\x00" * 24
        segment = b"\xff\xe2" + (len(mpf) + 2).to_bytes(2, "big") + mpf
        data = data[:2] + segment + data[2:] + small.getvalue()
    return data


class Camera:
    """Takes photos into a folder, with a clock that moves on between shots."""

    def __init__(self, folder: Path, start: datetime) -> None:
        self.folder = folder
        self.clock = start
        folder.mkdir(parents=True, exist_ok=True)

    def wait(self, seconds: float) -> None:
        self.clock += timedelta(seconds=seconds)

    def shoot(
        self,
        watch: int = 0,
        *,
        tags: str = "",
        size: tuple[int, int] = SIZE,
        turned: bool = False,
        gain_map: bool = False,
        settings: Settings = DEFAULT,
    ) -> Path:
        image = scene(watch, size)
        if turned:
            image = image.rotate(180)
        utc = self.clock - OFFSET
        name = f"PXL_{utc:%Y%m%d}_{utc:%H%M%S}{utc.microsecond // 1000:03d}{tags}.jpg"
        path = self.folder / name
        path.write_bytes(jpeg(image, exif_block(self.clock, settings), gain_map=gain_map))
        self.wait(1.2)
        return path

    def placement(self, watch: int, shots: int = 2, *, settings: Settings = DEFAULT) -> list[Path]:
        paths = [self.shoot(watch, settings=settings) for _ in range(shots)]
        self.wait(25)  # changing the watch
        return paths

    def block(self, watches: int = 3) -> None:
        """A slate, then the plan of block_rows(): re-seat, the others, re-seat."""
        self.shoot(99)  # the slate
        self.wait(20)
        order = [0, 0, *range(1, watches), 0, 0]
        for watch in order:
            self.placement(watch)


def write_plan(path: Path, rows: list[dict[str, str]]) -> Path:
    lines = [",".join(COLUMNS)] + [",".join(row.get(c, "") for c in COLUMNS) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def block_rows(
    session: str = "S03",
    watches: tuple[str, ...] = ("W01", "W02", "W03"),
    *,
    person: str = "P01",
    block: str = "T20-DAY",
    day: str = "2026-11-02",
) -> list[dict[str, str]]:
    """A block's plan: a re-seat check of the first watch at each end, the others between."""
    order = [watches[0], watches[0], *watches[1:], watches[0], watches[0]]
    reseat = {0, 1, len(order) - 2, len(order) - 1}
    return [
        {
            "session_id": session,
            "date": day,
            "person_id": person,
            "block": block,
            "surface": "backdrop",
            "seq": str(i + 1),
            "watch_id": w,
            "shots": "2",
            "reseat": "yes" if i in reseat else "",
        }
        for i, w in enumerate(order)
    ]
