# Generated from data/schemas/catalogue-entry.schema.json by scripts/contracts.py.
# Do not edit: change the schema, then run `uv run poe contracts`.

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
)


class CitedLength(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    value_mm: Annotated[StrictFloat, Field(gt=0.0, le=100.0)]
    """
    A length in millimetres
    """
    tolerance_mm: Annotated[StrictFloat, Field(gt=0.0, le=5.0)]
    """
    How far the true value may be from value_mm, from the precision the source gives it with
    """
    source: Annotated[StrictStr, Field(pattern="^S[0-9]{4}$")]
    """
    A source's ID in the catalogue's source list (S0001, S0002, ...)
    """


class CitedShape(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    value: Literal["round", "cushion", "tonneau", "square", "other"]
    """
    The case outline seen from above. 'square' covers rectangular cases too
    """
    source: Annotated[StrictStr, Field(pattern="^S[0-9]{4}$")]
    """
    A source's ID in the catalogue's source list (S0001, S0002, ...)
    """


class CitedBezelType(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    value: Literal["none", "smooth", "fluted", "rotating_insert", "other"]
    """
    The ring around the crystal
    """
    source: Annotated[StrictStr, Field(pattern="^S[0-9]{4}$")]
    """
    A source's ID in the catalogue's source list (S0001, S0002, ...)
    """


class CitedCaseMaterial(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    value: Literal["steel", "titanium", "gold", "ceramic", "resin", "bronze", "other"]
    """
    What the case is made of; gold covers yellow, rose and white gold, told apart by colour
    """
    source: Annotated[StrictStr, Field(pattern="^S[0-9]{4}$")]
    """
    A source's ID in the catalogue's source list (S0001, S0002, ...)
    """


class CitedColourName(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    value: Literal[
        "black",
        "white",
        "silver",
        "grey",
        "blue",
        "green",
        "red",
        "brown",
        "gold",
        "champagne",
        "cream",
        "orange",
        "yellow",
        "pink",
        "purple",
        "other",
    ]
    """
    A colour as a source or a person names it
    """
    source: Annotated[StrictStr, Field(pattern="^S[0-9]{4}$")]
    """
    A source's ID in the catalogue's source list (S0001, S0002, ...)
    """


class CitedStrapType(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    value: Literal["bracelet", "leather", "rubber", "fabric", "other"]
    """
    What the watch is worn on
    """
    source: Annotated[StrictStr, Field(pattern="^S[0-9]{4}$")]
    """
    A source's ID in the catalogue's source list (S0001, S0002, ...)
    """


class CitedCrownPosition(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    value: Annotated[StrictInt, Field(ge=1, le=12)]
    """
    Where the crown sits, as an hour on the dial (3 for most watches, 9 for a left-hand crown)
    """
    source: Annotated[StrictStr, Field(pattern="^S[0-9]{4}$")]
    """
    A source's ID in the catalogue's source list (S0001, S0002, ...)
    """


class Source(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[StrictStr, Field(pattern="^S[0-9]{4}$")]
    """
    A source's ID in the catalogue's source list (S0001, S0002, ...)
    """
    kind: Literal["manufacturer", "retailer", "review", "press", "other"]
    """
    Who published it. A manufacturer's own page is preferred
    """
    publisher: Annotated[StrictStr, Field(max_length=120, min_length=1)]
    title: Annotated[StrictStr, Field(max_length=300, min_length=1)]
    url: AnyUrl
    accessed: date
    """
    When the page was read
    """
    archived_url: AnyUrl | None
    """
    A web archive copy, so the citation survives the page changing
    """


class CatalogueEntry(BaseModel):
    """
    One watch reference with its published dimensions and appearance. Every value cites a source; a value no source gives is null (unknown), never guessed. This is the form the API serves; the files in data/catalogue store the same facts as rows.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    entry_version: Literal[1]
    """
    The version of this entry format
    """
    id: Annotated[StrictStr, Field(max_length=80, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$")]
    """
    Stable ID: the brand and reference in lower case, joined by hyphens
    """
    brand: Annotated[StrictStr, Field(max_length=60, min_length=1)]
    model: Annotated[StrictStr, Field(max_length=120, min_length=1)]
    reference: Annotated[StrictStr, Field(max_length=60, min_length=1)]
    """
    The manufacturer's reference number
    """
    aliases: list[StrictStr]
    """
    Nicknames people search with, for example a model's common short name
    """
    source: Annotated[StrictStr, Field(pattern="^S[0-9]{4}$")]
    """
    The main source: the brand, model and reference come from it, and so does any value without its own citation
    """
    case_shape: CitedShape
    case_diameter_mm: CitedLength | None
    """
    A cited length, or null when no source gives it
    """
    case_length_mm: CitedLength | None
    """
    A cited length, or null when no source gives it
    """
    bezel_diameter_mm: CitedLength | None
    """
    A cited length, or null when no source gives it
    """
    dial_opening_mm: CitedLength | None
    """
    A cited length, or null when no source gives it
    """
    lug_to_lug_mm: CitedLength | None
    """
    A cited length, or null when no source gives it
    """
    thickness_mm: CitedLength | None
    """
    A cited length, or null when no source gives it
    """
    lug_width_mm: CitedLength | None
    """
    A cited length, or null when no source gives it
    """
    bezel_type: CitedBezelType | None
    case_material: CitedCaseMaterial | None
    case_colour: CitedColourName | None
    dial_colour: CitedColourName | None
    strap_type: CitedStrapType | None
    crown_position: CitedCrownPosition | None
    sources: Annotated[list[Source], Field(min_length=1)]
    """
    Every source this entry cites, the main one first
    """
