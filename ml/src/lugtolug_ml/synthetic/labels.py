"""The labels written with every synthetic sample. They are exact: computed from the
scene, not drawn or estimated.

Points are in pixels in the image's own frame (x right, y down, (0, 0) at the top-left
corner), as in the benchmark's annotations; lengths are in millimetres.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from lugtolug_core.contracts.stand_in import StandInSpec

Point = Annotated[list[float], Field(min_length=2, max_length=2)]
Vector = Annotated[list[float], Field(min_length=3, max_length=3)]

CLASSES = {
    0: "background (the surface the arm lies on)",
    1: "skin",
    2: "strap",
    3: "lugs and crown",
    4: "case and bezel",
    5: "dial",
}


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CameraLabel(_Model):
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    rotation: Annotated[list[Vector], Field(min_length=3, max_length=3)]  # world to camera
    translation: Vector


class WatchPose(_Model):
    origin: Vector  # the centre of the case back
    u: Vector  # towards 3 o'clock
    v: Vector  # towards 12 o'clock
    w: Vector  # out of the dial


class Heights(_Model):
    """Heights above the case back of the edges the outlines follow."""

    dial: float
    case_top: float
    bezel_top: float
    thickness: float


class Outlines(_Model):
    """Edges of the watch projected into the image, each a closed list of points."""

    case_top: list[Point]  # the case body's top outer edge
    case_back: list[Point]  # its bottom edge, against the wrist
    bezel_top: list[Point] | None  # the bezel's outer top edge
    opening_top: list[Point]  # the dial opening at the crystal
    dial: list[Point]  # the dial opening at the dial's surface


class ReferenceCircle(_Model):
    """For a round case: the circle whose image calibrates the photo."""

    centre: Vector
    normal: Vector
    radius_mm: float


class ImageEllipse(_Model):
    cx: float
    cy: float
    a: float
    b: float
    angle: float


class WristLabel(_Model):
    width_mm: float
    thickness_mm: float
    circumference_mm: float
    hand_breadth_mm: float
    edges: list[Point] | None  # where the forearm's silhouette crosses the line through the watch


class Conditions(_Model):
    skin_tone: Annotated[int, Field(ge=1, le=10)]
    light: str
    light_elevation_deg: float
    light_azimuth_deg: float
    surface: str
    tilt_deg: float
    roll_deg: float
    distance_mm: float
    crown_towards_hand: bool
    dial_time: tuple[int, int, int]
    blur_px: float
    noise: float
    vignette: float
    jpeg_quality: int


class SyntheticLabels(_Model):
    sample_id: str
    generator: str
    seed: list[int]
    camera: CameraLabel
    watch: WatchPose
    spec: StandInSpec
    heights_mm: Heights
    outlines: Outlines
    reference_circle: ReferenceCircle | None
    case_top_ellipse: ImageEllipse | None  # the image of reference_circle
    px_per_mm: float  # at the centre of the case top, for a frontal view of that plane
    wrist: WristLabel
    conditions: Conditions
    pixel_counts: dict[int, int]  # pixels of each class
