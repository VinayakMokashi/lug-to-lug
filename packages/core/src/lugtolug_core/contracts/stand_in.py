# Generated from data/schemas/stand-in-spec.schema.json by scripts/contracts.py.
# Do not edit: change the schema, then run `uv run poe contracts`.

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
)


class Case(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    shape: Literal["round", "cushion", "tonneau", "square", "other"]
    """
    The case outline seen from above. 'square' covers rectangular cases too
    """
    diameter_mm: Annotated[StrictFloat, Field(gt=0.0, le=100.0)]
    """
    Across the case body from 9 to 3 o'clock, without the crown
    """
    length_mm: Annotated[StrictFloat, Field(gt=0.0, le=100.0)]
    """
    The case body from 12 to 6 o'clock, without the lugs. Equal to diameter_mm for a round case
    """
    squareness: Annotated[StrictFloat, Field(ge=2.0, le=20.0)]
    """
    Exponent of the superellipse that draws the outline: 2 is a circle or an ellipse, about 4 a cushion, 8 or more a square with small rounded corners
    """
    taper: Annotated[StrictFloat, Field(ge=0.5, le=1.0)]
    """
    Width at the 12 and 6 o'clock ends relative to the middle: 1 for most cases, about 0.8 for a tonneau
    """
    thickness_mm: Annotated[StrictFloat, Field(gt=0.0, le=30.0)]
    """
    From the case back to the top of the crystal
    """
    crystal_dome_mm: Annotated[StrictFloat, Field(ge=0.0, le=5.0)]
    """
    How far the crystal rises above the bezel or case top; 0 for a flat crystal
    """
    material: Literal["steel", "titanium", "gold", "ceramic", "resin", "bronze", "other"]
    """
    What the case is made of; gold covers yellow, rose and white gold, told apart by colour
    """
    finish: Literal["polished", "brushed", "matte"]
    """
    How the case surface reflects light
    """
    colour: Annotated[StrictStr, Field(pattern="^#[0-9a-f]{6}$")]
    """
    An sRGB colour as lower-case hex, for drawing
    """


class Bezel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    type: Literal["none", "smooth", "fluted", "rotating_insert", "other"]
    """
    The ring around the crystal
    """
    outer_mm: Annotated[StrictFloat | None, Field(gt=0.0, le=100.0)]
    """
    Outer width of the bezel or top ring from 9 to 3 o'clock; null when there is no separate bezel
    """
    colour: Annotated[StrictStr | None, Field(pattern="^#[0-9a-f]{6}$")]
    """
    The bezel's own colour; null when there is no separate bezel
    """
    insert_colour: Annotated[StrictStr | None, Field(pattern="^#[0-9a-f]{6}$")]
    """
    Colour of a rotating bezel's insert; null for other bezels
    """
    markings: Literal["none", "minutes", "dive", "gmt", "tachymeter"]
    """
    A generic scale drawn on the bezel. Never text or logos
    """


class Dial(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    opening_mm: Annotated[StrictFloat, Field(gt=0.0, le=100.0)]
    """
    Width of the visible dial opening (the inner edge of the bezel or case) from 9 to 3 o'clock. The opening follows the case outline's shape
    """
    colour: Annotated[StrictStr, Field(pattern="^#[0-9a-f]{6}$")]
    """
    An sRGB colour as lower-case hex, for drawing
    """
    index_style: Literal["baton", "arabic", "roman", "dots", "none"]
    """
    Generic hour markers. Never text or logos
    """
    index_colour: Annotated[StrictStr, Field(pattern="^#[0-9a-f]{6}$")]
    """
    An sRGB colour as lower-case hex, for drawing
    """
    hands_colour: Annotated[StrictStr, Field(pattern="^#[0-9a-f]{6}$")]
    """
    An sRGB colour as lower-case hex, for drawing
    """


class Lugs(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    lug_to_lug_mm: Annotated[StrictFloat, Field(gt=0.0, le=100.0)]
    """
    From the tip of the upper lugs to the tip of the lower lugs, along 12 to 6 o'clock
    """
    lug_width_mm: Annotated[StrictFloat, Field(gt=0.0, le=100.0)]
    """
    Inside distance between the lugs, where the strap fits
    """
    style: Literal["standard", "integrated"]
    """
    'integrated' when the strap or bracelet joins the case without separate lugs
    """


class Crown(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    position: Annotated[StrictInt, Field(ge=1, le=12)]
    """
    Where the crown sits, as an hour on the dial (3 for most watches, 9 for a left-hand crown)
    """
    diameter_mm: Annotated[StrictFloat, Field(gt=0.0, le=15.0)]
    """
    Diameter of the crown
    """
    length_mm: Annotated[StrictFloat, Field(gt=0.0, le=15.0)]
    """
    How far the crown stands out from the case
    """
    guards: StrictBool
    """
    Whether the case has crown guards
    """


class Strap(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    type: Literal["bracelet", "leather", "rubber", "fabric", "other"]
    """
    What the watch is worn on
    """
    colour: Annotated[StrictStr, Field(pattern="^#[0-9a-f]{6}$")]
    """
    An sRGB colour as lower-case hex, for drawing
    """
    width_at_buckle_mm: Annotated[StrictFloat, Field(gt=0.0, le=100.0)]
    """
    Strap width at the buckle or clasp; equal to the lug width when it doesn't taper
    """


class StandInSpec(BaseModel):
    """
    Everything needed to draw a watch at its true size without brand marks: the outline, the layers seen from above, and the colours. The 2.5-D renderer, the 3-D stand-in for live AR and the synthetic data generator all draw from it. Lengths are nominal; their uncertainty lives in the catalogue.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    spec_version: Literal[1]
    """
    The version of this specification format
    """
    case: Case
    bezel: Bezel
    dial: Dial
    lugs: Lugs
    crown: Crown
    strap: Strap
    assumed: list[StrictStr]
    """
    Dimensions filled with a default rather than from a measurement or a cited source, as 'section.field' paths (for example 'lugs.lug_to_lug_mm'). A render that depends on one says so. Colours, finish and markings are always approximate in a stand-in and are never listed.
    """
