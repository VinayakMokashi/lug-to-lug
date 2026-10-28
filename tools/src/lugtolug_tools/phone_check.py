"""Check a handful of test photos against the Pixel 9a settings sheet.

    uv run poe phone-check <folder of test photos>

Some of what the settings sheet (docs/data/pixel-9a-settings.md) asks for can't be
confirmed from documentation, only from the files the phone writes: whether a focus
and exposure lock survives a series of remote shots, whether turning Ultra HDR off
removes the gain map, whether the phone keeps the same way up when it points straight
down. The sheet's test series answers them; this command reads the series and reports
each check as PASS, FAIL or INFO.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from PIL import Image, ImageCms

from lugtolug_tools.ingest import CAMERA, MIN_FOCUS_M, looks_turned, thumbnail
from lugtolug_tools.jpeg import scan
from lugtolug_tools.photos import Photo, read_photo

MAIN_LENS_MM = 4.53
FULL_FRAME = frozenset({(4000, 3000), (3000, 4000)})


@dataclass(frozen=True)
class Check:
    name: str
    status: str  # PASS, FAIL or INFO
    detail: str


def _gain_map(path: Path) -> bool:
    """Whether the file carries more than one image: an HDR gain map or a video."""
    data = path.read_bytes()
    found, end = scan(data)
    mpf = any(s.marker == 0xE2 and s.payload.startswith(b"MPF\x00") for s in found)
    return mpf or len(data) - end > 16


def _colour_profile(path: Path) -> str:
    with Image.open(path) as image:
        icc = image.info.get("icc_profile")
    if not icc:
        return "none"
    profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
    return ImageCms.getProfileDescription(profile).strip()


def _spread(values: Sequence[float]) -> float:
    return (max(values) - min(values)) / max(values) if values and max(values) > 0 else 0.0


def check_phone(
    photos: Sequence[Photo], frame: frozenset[tuple[int, int]] = FULL_FRAME
) -> list[Check]:
    if not photos:
        return [Check("photos", "FAIL", "no JPEGs found")]
    photos = sorted(photos, key=lambda p: (p.captured is None, p.captured, p.path.name))
    n = len(photos)
    checks: list[Check] = []

    def add(name: str, ok: bool, good: str, bad: str) -> None:
        checks.append(Check(name, "PASS" if ok else "FAIL", good if ok else bad))

    models = sorted({p.model for p in photos})
    add("camera", models == [CAMERA], CAMERA, f"models: {', '.join(models)}")
    lenses = sorted({f"{p.focal_length_mm} mm" for p in photos})
    add(
        "main lens",
        all(p.focal_length_mm == MAIN_LENS_MM for p in photos),
        f"all {MAIN_LENS_MM} mm",
        f"focal lengths: {', '.join(lenses)} (0.5x is 1.835 mm)",
    )
    zoomed = [p.path.name for p in photos if p.zoomed]
    add("1x zoom", not zoomed, "no digital zoom", f"zoomed: {', '.join(zoomed)}")
    sizes = sorted({f"{p.width}x{p.height}" for p in photos})
    add(
        "full 4:3 frame",
        all((p.width, p.height) in frame for p in photos),
        f"{', '.join(sizes)}",
        f"sizes: {', '.join(sizes)} (Full image (4:3) is 4000x3000)",
    )
    add(
        "same way up",
        len(sizes) == 1,
        "every photo has the same size",
        f"the phone turned during the series: {', '.join(sizes)}",
    )
    previous = None
    flipped = []
    for p in photos:
        thumb = thumbnail(p)
        if previous is not None and looks_turned(previous, thumb):
            flipped.append(p.path.name)
        previous = thumb
    add("not upside down", not flipped, "no photo turned 180", f"turned: {', '.join(flipped)}")
    modes = [f"{p.path.name} ({', '.join(p.deviations)})" for p in photos if p.deviations]
    add("plain photo mode", not modes, "no Night Sight, motion, portrait or RAW", "; ".join(modes))
    located = [p.path.name for p in photos if p.has_location]
    add("location off", not located, "no latitude or longitude", f"located: {', '.join(located)}")
    gain_maps = [p.path.name for p in photos if _gain_map(p.path)]
    add(
        "Ultra HDR off",
        not gain_maps,
        "one image per file, no gain map",
        f"{len(gain_maps)} of {n} files carry a second image (gain map or video)",
    )
    profiles = sorted({_colour_profile(p.path) for p in photos})
    add(
        "sRGB colour",
        all("srgb" in profile.lower() for profile in profiles),
        ", ".join(profiles),
        f"profiles: {', '.join(profiles)} (Rich colour / Display P3 should be off)",
    )
    near = [p.path.name for p in photos if (p.subject_distance_m or 1.0) < MIN_FOCUS_M]
    add("not macro", not near, "focus outside macro range", f"too close: {', '.join(near)}")

    distances = [p.subject_distance_m for p in photos if p.subject_distance_m is not None]
    exposures = [p.exposure_s for p in photos if p.exposure_s is not None]
    isos = [float(p.iso) for p in photos if p.iso is not None]
    held = _spread(distances) <= 0.01 and _spread(exposures) == 0 and _spread(isos) == 0
    checks.append(
        Check(
            "focus and exposure lock held",
            "PASS" if held else "INFO",
            f"focus {min(distances, default=0):.3f}-{max(distances, default=0):.3f} m, "
            f"exposure {min(exposures, default=0):.5f}-{max(exposures, default=0):.5f} s, "
            f"ISO {min(isos, default=0):.0f}-{max(isos, default=0):.0f}"
            + ("" if held else " (they changed: the lock did not hold, or wasn't set)"),
        )
    )
    times = [p.captured for p in photos if p.captured]
    if len(times) == n and n > 1:
        gaps = [(b - a).total_seconds() for a, b in pairwise(times)]
        checks.append(
            Check(
                "timing",
                "INFO",
                f"{n} photos over {(times[-1] - times[0]).total_seconds():.0f} s; "
                f"gaps {min(gaps):.1f}-{max(gaps):.1f} s",
            )
        )
    headings = sum(1 for p in photos if p.has_heading)
    checks.append(
        Check("compass heading", "INFO", f"{headings} of {n} files carry one (removed at ingest)")
    )
    size = sum(p.path.stat().st_size for p in photos) / n / 1e6
    checks.append(Check("file size", "INFO", f"{size:.1f} MB on average"))
    return checks


def run(folder: Path) -> tuple[list[Check], list[str]]:
    jpegs = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg"))
    others = sorted(
        p.name
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() not in (".jpg", ".jpeg")
    )
    return check_phone([read_photo(p) for p in jpegs]), others
