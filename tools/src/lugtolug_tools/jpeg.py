"""Remove a JPEG's metadata without touching its pixels.

Re-encoding a JPEG changes its pixels, so metadata is removed at the level of the
file's segments instead: the compressed image data is copied byte for byte, and only the
metadata segments are dropped or replaced. The result decodes to exactly the same
pixels; a test checks that.

What is kept: the segments needed to decode the image, the ICC colour profile, and the
Adobe segment (which changes how colours decode). What is dropped: EXIF (replaced by the
caller's), XMP, comments, every other application segment, and anything after the first
image's end, such as a phone's HDR gain map or a motion-photo video.
"""

from __future__ import annotations

from dataclasses import dataclass

SOI = 0xD8
EOI = 0xD9
SOS = 0xDA
APP1 = 0xE1
APP2 = 0xE2
APP14 = 0xEE
COM = 0xFE
_STANDALONE = frozenset({0x01, *range(0xD0, 0xD8)})  # TEM and the restart markers


class JpegError(ValueError):
    """The bytes are not a JPEG this module can read."""


@dataclass(frozen=True)
class Segment:
    marker: int
    data: bytes  # the whole segment, marker included; for SOS, the scan data after it too

    @property
    def payload(self) -> bytes:
        return self.data[4:]


def segments(jpeg: bytes) -> list[Segment]:
    """The segments of the file's first image, from after SOI up to its EOI."""
    return scan(jpeg)[0]


def scan(jpeg: bytes) -> tuple[list[Segment], int]:
    """The first image's segments, and the offset just past its EOI.

    Bytes after that offset belong to something else: an HDR gain map, a motion
    photo's video, or junk.
    """
    if jpeg[:2] != b"\xff\xd8":
        raise JpegError("not a JPEG: no start-of-image marker")
    found: list[Segment] = []
    i, n = 2, len(jpeg)
    while True:
        if i + 1 >= n:
            raise JpegError("the file ends before the end-of-image marker")
        if jpeg[i] != 0xFF:
            raise JpegError(f"expected a marker at byte {i}")
        while jpeg[i + 1] == 0xFF:  # fill bytes before a marker
            i += 1
            if i + 1 >= n:
                raise JpegError("the file ends inside a marker")
        marker = jpeg[i + 1]
        if marker == EOI:
            return found, i + 2
        if marker == SOI:
            raise JpegError(f"a second start-of-image marker at byte {i}")
        if marker in _STANDALONE:
            found.append(Segment(marker, jpeg[i : i + 2]))
            i += 2
            continue
        if i + 4 > n:
            raise JpegError("the file ends inside a segment header")
        end = i + 2 + int.from_bytes(jpeg[i + 2 : i + 4], "big")
        if end > n or end < i + 4:
            raise JpegError(f"a segment at byte {i} runs past the end of the file")
        if marker != SOS:
            found.append(Segment(marker, jpeg[i:end]))
            i = end
            continue
        # The scan data runs to the next marker that isn't a stuffed byte (FF 00), a restart
        # marker (FF D0-D7) or a fill byte (FF FF).
        j = end
        while True:
            j = jpeg.find(b"\xff", j)
            if j < 0 or j + 1 >= n:
                raise JpegError("the scan data runs past the end of the file")
            following = jpeg[j + 1]
            if following == 0xFF:
                j += 1
            elif following == 0x00 or 0xD0 <= following <= 0xD7:
                j += 2
            else:
                break
        found.append(Segment(SOS, jpeg[i:j]))
        i = j


def _kept(segment: Segment) -> bool:
    if segment.marker == APP2:
        return segment.payload.startswith(b"ICC_PROFILE\x00")
    if segment.marker == APP14:
        return segment.payload.startswith(b"Adobe")
    return not (0xE0 <= segment.marker <= 0xEF or segment.marker == COM)


def strip_metadata(jpeg: bytes, exif: bytes | None = None) -> bytes:
    """The same image with only the decoding segments, its colour profile and `exif`.

    `exif` is a complete EXIF block starting with b"Exif\\0\\0" (as Pillow's
    `Image.Exif.tobytes()` returns it), or None for no EXIF at all.
    """
    head = b"\xff\xd8"
    if exif is not None:
        if not exif.startswith(b"Exif\x00\x00"):
            raise ValueError("the EXIF block must start with Exif\\0\\0")
        if len(exif) > 0xFFFF - 2:
            raise ValueError("the EXIF block is too large for one segment")
        head += b"\xff\xe1" + (len(exif) + 2).to_bytes(2, "big") + exif
    body = b"".join(s.data for s in segments(jpeg) if _kept(s))
    return head + body + b"\xff\xd9"
