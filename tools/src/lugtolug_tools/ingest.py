"""Ingest a session: match the photos to the plan, strip their metadata, write manifests.

    uv run poe ingest S03            # check, then write
    uv run poe ingest S03 --dry-run  # check only

The plan says what each photo shows; the camera roll only says in which order the
photos were taken. Matching the two is where a mistake would silently mislabel the
benchmark, so the ingest never guesses. Three checks must agree:

1. **Count.** One slate, then each placement's `shots`, must add up to the photos found.
2. **Timing.** Photos taken within a few seconds of each other belong to one placement;
   changing the watch takes longer. The groups the timing shows must match the plan's
   placements one for one, so an extra photo of one watch and a missing photo of the
   next can't cancel out.
3. **Camera.** One phone, one lens, no zoom and one image size for the whole session;
   plain photo mode; the same way up as the photo before; capture dates that match the
   plan.

Only then are the photos copied, renamed and stripped. Otherwise the report shows where
the plan and the photos part ways, and the plan's `shots` is corrected by hand. A photo
the phone stored turned (it decides which way is up from gravity, which is ambiguous
when it points straight down) is recorded with --turned once a person has checked it,
never corrected silently.
"""

from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from lugtolug_tools.jpeg import strip_metadata
from lugtolug_tools.photos import Photo, kept_exif, read_photo
from lugtolug_tools.plan import UNCHOSEN, Placement

DEFAULT_GAP_S = 8.0
CAMERA = "Pixel 9a"
# The rig holds the phone about 30 cm up. Pixel 9a macro focus starts around 5 cm, so
# a focus distance this short means the phone was far too close.
MIN_FOCUS_M = 0.15
TURNS = (90, 180, 270)
IGNORED_FILES = frozenset({"desktop.ini", "thumbs.db", ".ds_store"})

PUBLIC_COLUMNS = (
    "image_id",
    "session_id",
    "person_id",
    "block",
    "surface",
    "seq",
    "watch_id",
    "shot",
    "reseat",
    "sha256",
    "width",
    "height",
    "turned_deg",
    "camera",
    "lens",
    "focal_length_mm",
    "focal_length_35mm",
    "digital_zoom",
    "subject_distance_m",
    "f_number",
    "exposure_s",
    "iso",
)
PRIVATE_COLUMNS = ("image_id", "role", "original", "original_sha256", "captured", "group")


@dataclass(frozen=True)
class Match:
    photo: Photo
    placement: Placement | None  # None for a slate
    shot: int  # from 1 within its placement; 0 for a slate
    group: int  # its timing group, from 0 (the slate)

    @property
    def image_id(self) -> str | None:
        return None if self.placement is None else self.placement.image_id(self.shot)


@dataclass
class Report:
    session_id: str
    found: int = 0
    expected: int = 0
    planned: list[int] = field(default_factory=list)  # photos per group, slate first
    timed: list[int] = field(default_factory=list)  # photos per group by timing
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    matches: list[Match] = field(default_factory=list)
    written: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        lines = [
            f"Session {self.session_id}: {self.found} photos found, {self.expected} planned",
            f"  groups by timing: {len(self.timed)}, by plan: {len(self.planned)}",
        ]
        lines += [f"  ERROR   {e}" for e in self.errors]
        lines += [f"  warning {w}" for w in self.warnings]
        lines += [f"  wrote   {w}" for w in self.written]
        lines.append("  OK" if self.ok else "  Nothing was written.")
        return "\n".join(lines)


def session_photos(folder: Path) -> tuple[list[Photo], list[str]]:
    """The JPEGs in a session folder, and the names of any other files in it."""
    photos, others = [], []
    for path in sorted(folder.iterdir()):
        if path.is_dir() or path.name.lower() in IGNORED_FILES:
            continue
        if path.suffix.lower() in (".jpg", ".jpeg"):
            photos.append(read_photo(path))
        else:
            others.append(path.name)
    return photos, others


def group_by_time(photos: Sequence[Photo], gap_s: float) -> list[list[Photo]]:
    """Photos in capture order, split wherever more than `gap_s` seconds pass."""
    groups: list[list[Photo]] = []
    for photo in photos:
        previous = groups[-1][-1] if groups else None
        if (
            previous is None
            or previous.captured is None
            or photo.captured is None
            or (photo.captured - previous.captured).total_seconds() > gap_s
        ):
            groups.append([photo])
        else:
            groups[-1].append(photo)
    return groups


def _describe(index: int, placements: Sequence[Placement]) -> str:
    if index == 0:
        return "the slate"
    p = placements[index - 1]
    return f"placement {p.seq} ({p.watch_id}{', re-seat' if p.reseat else ''})"


def _span(group: Sequence[Photo]) -> str:
    times = [p.captured.strftime("%H:%M:%S") for p in group if p.captured]
    return f"{times[0]}-{times[-1]}" if times else "unknown times"


def _upright(photo: Photo, turned: Mapping[str, int]) -> tuple[int, int]:
    """The photo's size once a recorded turn is undone."""
    if turned.get(photo.path.name, 0) in (90, 270):
        return photo.height, photo.width
    return photo.width, photo.height


def check_camera(
    photos: Sequence[Photo], report: Report, turned: Mapping[str, int] | None = None
) -> None:
    """Rules every photo of a session must meet, whatever the plan says."""
    turned = turned or {}
    if not photos:
        return
    first = photos[0]
    for photo in photos:
        name = photo.path.name
        if photo.captured is None:
            report.errors.append(f"{name}: no capture time in its EXIF, so it can't be ordered")
        if photo.model != CAMERA:
            report.errors.append(f"{name}: taken with {photo.model or 'an unknown camera'}")
        if photo.deviations:
            report.errors.append(f"{name}: not a plain photo ({', '.join(photo.deviations)})")
        if photo.zoomed:
            report.errors.append(f"{name}: zoomed in ({photo.digital_zoom:g}x); use 1x only")
        if photo.lens != first.lens or photo.focal_length_mm != first.focal_length_mm:
            report.errors.append(
                f"{name}: lens {photo.lens or photo.focal_length_mm}, but the session started "
                f"with {first.lens or first.focal_length_mm}"
            )
        if _upright(photo, turned) != _upright(first, turned):
            report.errors.append(
                f"{name}: {photo.width}x{photo.height}, but the session started at "
                f"{first.width}x{first.height} (the phone turned, or the ratio changed)"
            )
        if photo.subject_distance_m is not None and photo.subject_distance_m < MIN_FOCUS_M:
            report.errors.append(
                f"{name}: focused at {photo.subject_distance_m:.2f} m, in macro range; "
                "the phone was too close"
            )
        if photo.orientation != 1:
            report.warnings.append(f"{name}: orientation tag {photo.orientation} (expected 1)")
    located = [p.path.name for p in photos if p.has_location]
    if located:
        report.warnings.append(
            f"{len(located)} photo(s) carry a location (removed in the copies): "
            "turn the camera's Save location setting off"
        )
    by_hash: dict[str, str] = {}
    for photo in photos:
        if photo.sha256 in by_hash:
            report.errors.append(f"{photo.path.name} is the same file as {by_hash[photo.sha256]}")
        by_hash.setdefault(photo.sha256, photo.path.name)


def thumbnail(photo: Photo, turn: int = 0) -> Image.Image:
    """A small grey version of the photo, turned back by its recorded turn."""
    with Image.open(photo.path) as image:
        image.draft("L", (image.width // 8, image.height // 8))
        small = image.convert("L")
    if turn:
        small = small.rotate(turn, expand=True)
    return small.resize((48, 36))


def _difference(a: Image.Image, b: Image.Image) -> float:
    return float(ImageStat.Stat(ImageChops.difference(a, b)).mean[0])


def looks_turned(previous: Image.Image, current: Image.Image) -> bool:
    """Whether `current` matches `previous` much better after turning it 180 degrees.

    Within a block only the watch changes, so consecutive photos are nearly identical;
    a photo the phone stored upside down differs everywhere, until it is turned back.
    """
    as_is = _difference(previous, current)
    turned = _difference(previous, current.rotate(180))
    # Consecutive photos in a block differ by a few grey levels at most (the watch), so
    # a turn shows as a clearly larger difference that turning back removes.
    return as_is > 4 and turned * 1.5 < as_is


def check_turns(
    matches: Sequence[Match], report: Report, turned: Mapping[str, int] | None = None
) -> None:
    """Flag photos that look upside down next to the photo before them."""
    turned = turned or {}
    previous: Image.Image | None = None
    for m in matches:
        if m.placement is None:
            continue
        current = thumbnail(m.photo, turned.get(m.photo.path.name, 0))
        if previous is not None and looks_turned(previous, current):
            report.errors.append(
                f"{m.photo.path.name} ({m.image_id}) looks turned 180 degrees next to the photo "
                f"before it; check it, then record it with --turned {m.photo.path.name}=180"
            )
            continue  # the next photo is compared with the last one the right way up
        previous = current


def match(
    placements: Sequence[Placement],
    photos: Sequence[Photo],
    *,
    slates: int = 1,
    gap_s: float = DEFAULT_GAP_S,
    trust_order: bool = False,
    turned: Mapping[str, int] | None = None,
) -> Report:
    """Pair photos with the plan's placements, or report exactly why they can't be."""
    turned = turned or {}
    report = Report(session_id=placements[0].session_id if placements else "?")
    unchosen = [p.seq for p in placements if p.watch_id == UNCHOSEN]
    if unchosen:
        report.errors.append(f"the plan has no watch chosen for placements {unchosen}")
    for p in placements:
        if p.shots == 0:
            report.warnings.append(f"placement {p.seq} ({p.watch_id}) has no photos in the plan")
    names = {p.path.name for p in photos}
    for name, degrees in turned.items():
        if name not in names:
            report.errors.append(f"--turned names {name}, which isn't in the session")
        if degrees not in TURNS:
            report.errors.append(f"--turned {name}={degrees}: a turn is 90, 180 or 270")

    ordered = sorted(photos, key=lambda p: (p.captured is None, p.captured, p.path.name))
    check_camera(ordered, report, turned)
    shooting = [p for p in placements if p.shots > 0]
    report.planned = [slates] + [p.shots for p in shooting]
    report.found, report.expected = len(ordered), sum(report.planned)
    groups = group_by_time(ordered, gap_s)
    report.timed = [len(g) for g in groups]

    if report.found != report.expected:
        report.errors.append(
            f"{report.found} photos, but the plan expects {report.expected} "
            f"({slates} slate + {report.expected - slates} for {len(shooting)} placements)"
        )
    if report.timed != report.planned:
        pairs = zip(report.timed, report.planned, strict=False)
        k = next(
            (i for i, (a, b) in enumerate(pairs) if a != b),
            min(len(report.timed), len(report.planned)),
        )
        if k < len(report.planned) and k < len(groups):
            detail = (
                f"the plan expects {report.planned[k]} photo(s) of {_describe(k, shooting)}, "
                f"but {report.timed[k]} were taken together at {_span(groups[k])}"
            )
        else:
            detail = (
                f"the timing shows {len(groups)} groups of photos and the plan "
                f"{len(report.planned)} (one slate plus each placement)"
            )
        message = f"timing and plan disagree from group {k}: {detail}"
        if trust_order and report.found == report.expected:
            report.warnings.append(f"{message}; matched in order anyway (--trust-order)")
        else:
            report.errors.append(message)
    if not report.ok:
        return report

    photo_iter = iter(ordered)
    plan = [(None, slates)] + [(p, p.shots) for p in shooting]
    for group, (placement, count) in enumerate(plan):
        for shot in range(1, count + 1):
            photo = next(photo_iter)
            report.matches.append(Match(photo, placement, 0 if placement is None else shot, group))
            day = placement.date if placement else (shooting[0].date if shooting else None)
            if day and photo.captured and photo.captured.date() != day:
                report.errors.append(
                    f"{photo.path.name}: taken on {photo.captured.date()}, the plan says {day}"
                )
    check_turns(report.matches, report, turned)
    return report


def _csv(columns: tuple[str, ...], rows: list[dict[str, object]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _value(number: float | None) -> str:
    return "" if number is None else f"{number:.6g}"


def ingest(
    placements: Sequence[Placement],
    raw: Path,
    *,
    work: Path,
    manifests: Path,
    private_manifests: Path,
    dry_run: bool = False,
    replace: bool = False,
    slates: int = 1,
    gap_s: float = DEFAULT_GAP_S,
    trust_order: bool = False,
    turned: Mapping[str, int] | None = None,
) -> Report:
    """Check a session folder against its plan, then write the copies and manifests.

    `raw` is the session's folder of originals, which is only read. The stripped copies
    go to `work`, the public manifest to `manifests` and the private one (original names
    and capture times) to `private_manifests`, each as <session>.csv.
    """
    turned = turned or {}
    session_id = placements[0].session_id
    if not raw.is_dir():
        return Report(session_id, errors=[f"no folder of photos at {raw}"])
    photos, others = session_photos(raw)
    report = match(
        placements, photos, slates=slates, gap_s=gap_s, trust_order=trust_order, turned=turned
    )
    if others:
        report.errors.append(f"files that aren't JPEGs: {', '.join(others)}")
    if not report.ok:
        return report

    copies: dict[str, bytes] = {}
    public: list[dict[str, object]] = []
    private: list[dict[str, object]] = []
    for m in report.matches:
        photo = m.photo
        private.append(
            {
                "image_id": m.image_id or "",
                "role": "slate" if m.placement is None else "photo",
                "original": photo.path.name,
                "original_sha256": photo.sha256,
                "captured": photo.captured.isoformat(timespec="milliseconds")
                if photo.captured
                else "",
                "group": m.group,
            }
        )
        if m.placement is None or m.image_id is None:
            continue
        copy = strip_metadata(photo.path.read_bytes(), kept_exif(photo.path))
        with Image.open(io.BytesIO(copy)) as a, Image.open(photo.path) as b:
            if a.tobytes() != b.tobytes():
                report.errors.append(f"{photo.path.name}: the copy decodes differently")
        copies[m.image_id] = copy
        p = m.placement
        public.append(
            {
                "image_id": m.image_id,
                "session_id": p.session_id,
                "person_id": p.person_id,
                "block": p.block,
                "surface": p.surface,
                "seq": p.seq,
                "watch_id": p.watch_id,
                "shot": m.shot,
                "reseat": "yes" if p.reseat else "",
                "sha256": hashlib.sha256(copy).hexdigest(),
                "width": photo.width,
                "height": photo.height,
                "turned_deg": turned.get(photo.path.name, 0),
                "camera": photo.model,
                "lens": photo.lens,
                "focal_length_mm": _value(photo.focal_length_mm),
                "focal_length_35mm": photo.focal_length_35mm or "",
                "digital_zoom": _value(photo.digital_zoom),
                "subject_distance_m": _value(photo.subject_distance_m),
                "f_number": _value(photo.f_number),
                "exposure_s": _value(photo.exposure_s),
                "iso": photo.iso or "",
            }
        )

    outputs = {
        manifests / f"{session_id}.csv": _csv(PUBLIC_COLUMNS, public),
        private_manifests / f"{session_id}.csv": _csv(PRIVATE_COLUMNS, private),
    }
    for path, content in outputs.items():
        if path.exists() and path.read_text(encoding="utf-8") != content and not replace:
            report.errors.append(f"{path.name} in {path.parent.name}/ differs; use --replace")
    if not report.ok or dry_run:
        if dry_run and report.ok:
            report.warnings.append(f"dry run: {len(copies)} copies and 2 manifests not written")
        return report

    folder = work / session_id
    folder.mkdir(parents=True, exist_ok=True)
    for stale in folder.glob("*.jpg"):
        if stale.stem not in copies:
            stale.unlink()
    for image_id, data in copies.items():
        (folder / f"{image_id}.jpg").write_bytes(data)
    report.written.append(f"{len(copies)} copies in {folder}")
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        report.written.append(str(path))
    return report
