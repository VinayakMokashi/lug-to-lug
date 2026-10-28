# Generated from data/schemas/annotation.schema.json by scripts/contracts.py.
# Do not edit: change the schema, then run `uv run poe contracts`.

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
)


class Point(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    x: StrictFloat
    y: StrictFloat


class Flags(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    blurred: StrictBool
    glare: StrictBool
    """
    A reflection hides part of the case or dial
    """
    occluded: StrictBool
    """
    Something covers part of the watch or the wrist
    """
    strap_moved: StrictBool
    """
    The watch sits away from its usual place
    """
    unusable: StrictBool
    """
    Leave this photo out of every measurement
    """
    note: Annotated[StrictStr, Field(max_length=500)]


class Provenance(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    method: Literal[
        "person_drawn",
        "model_proposed_person_accepted",
        "model_proposed_person_corrected",
        "model_only",
        "session_sheet",
    ]
    """
    How the label was made. Only the first three were checked by a person
    """
    labeller: Annotated[StrictStr | None, Field(pattern="^P[0-9]{2}$")]
    """
    The person who drew, accepted or corrected the label, by participant ID; null when no person checked it
    """
    proposer: Annotated[StrictStr | None, Field(max_length=120)]
    """
    The model or algorithm, with its version, that proposed the label; null when a person drew it
    """
    tool: Annotated[StrictStr, Field(max_length=120, min_length=1)]
    """
    The tool and version that saved the label
    """
    created: AwareDatetime
    """
    When the label was saved, with its time zone
    """


class Outline(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    points: Annotated[list[Point], Field(min_length=5)]
    """
    Points on the edge, in order around it. Five or more, so an ellipse is determined
    """
    provenance: Provenance


class WristEdges(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    radial: Annotated[list[Point], Field(min_length=2)]
    """
    The skin edge on the thumb side, across the watch's position
    """
    ulnar: Annotated[list[Point], Field(min_length=2)]
    """
    The skin edge on the little-finger side, across the watch's position
    """
    provenance: Provenance


class Identity(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    watch_id: Annotated[StrictStr, Field(pattern="^W[0-9]{2,3}$")]
    """
    A reference watch's ID (W01, W02, ...)
    """
    provenance: Provenance


class ImageAnnotation(BaseModel):
    """
    The labels of one benchmark photo. Points are in pixels of the image as stored, before any rotation from its orientation tag: x to the right, y down, (0, 0) at the top-left corner of the top-left pixel. Every label records how it was made.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    annotation_version: Literal[1]
    """
    The version of this annotation format
    """
    image_id: Annotated[StrictStr, Field(max_length=80, pattern="^[A-Za-z0-9_-]+$")]
    """
    The photo's benchmark name without its extension, as in the session manifest
    """
    image_sha256: Annotated[StrictStr, Field(pattern="^[0-9a-f]{64}$")]
    """
    SHA-256 of the benchmark file the labels were made on
    """
    width: Annotated[StrictInt, Field(ge=1)]
    """
    Stored width in pixels
    """
    height: Annotated[StrictInt, Field(ge=1)]
    """
    Stored height in pixels
    """
    case_outline: Outline | None
    """
    The outer edge of the case seen from above (the bezel's edge where it is outermost)
    """
    dial_outline: Outline | None
    """
    The edge of the visible dial opening
    """
    wrist_edges: WristEdges | None
    identity: Identity | None
    flags: Flags
