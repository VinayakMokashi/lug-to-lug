"""Stand-in specifications: building one from what is known, and the rules a valid one obeys.

A stand-in is drawn from its dimensions alone, so every length matters. When a
dimension is unknown, build_spec() fills it from typical proportions and lists it in
`assumed`, so a render that depends on it can say so. Colours, finish and markings are
always approximate in a stand-in and are never listed.

check_spec() holds the rules JSON Schema can't express, such as "the dial opening is
smaller than the case".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lugtolug_core.contracts.stand_in import Bezel, Case, Crown, Dial, Lugs, StandInSpec, Strap
from lugtolug_core.vocab import BezelType, CaseMaterial, CaseShape, ColourName, StrapType

# The dimensions a default may fill, as `section.field` paths.
ASSUMABLE = frozenset(
    {
        "case.length_mm",
        "case.squareness",
        "case.taper",
        "case.thickness_mm",
        "case.crystal_dome_mm",
        "bezel.outer_mm",
        "dial.opening_mm",
        "lugs.lug_to_lug_mm",
        "lugs.lug_width_mm",
        "crown.position",
        "crown.diameter_mm",
        "crown.length_mm",
        "strap.width_at_buckle_mm",
    }
)

# Drawing colours for the named colours sources use.
PALETTE: dict[ColourName, str] = {
    "black": "#1b1b1d",
    "white": "#f2f2ee",
    "silver": "#c7c9cc",
    "grey": "#7d8084",
    "blue": "#1f3f7a",
    "green": "#1e5a3c",
    "red": "#8e1f24",
    "brown": "#5a3a26",
    "gold": "#c9a54a",
    "champagne": "#d8c49a",
    "cream": "#efe6cf",
    "orange": "#e0702a",
    "yellow": "#e8c547",
    "pink": "#e3a5b0",
    "purple": "#5b3c7a",
    "other": "#808080",
}

# Outline of each non-round shape: superellipse exponent, taper, and length relative
# to the diameter. No source publishes these, so they are always assumed.
_SHAPE_OUTLINE: dict[CaseShape, tuple[float, float, float]] = {
    "cushion": (4.0, 1.0, 1.0),
    "tonneau": (3.0, 0.8, 1.3),
    "square": (10.0, 1.0, 1.0),
    "other": (3.0, 1.0, 1.0),
}

# Typical proportions, as fractions of the case diameter.
_THICKNESS = 0.3
_LUG_TO_LUG = 1.2
# Lugs reach past the case body, so lug-to-lug is at least this much of the case length.
_LUG_TO_LUG_OF_LENGTH = 1.1
_LUG_WIDTH = 0.5
_CROWN_DIAMETER = 0.15
_CROWN_LENGTH_MM = 2.5
# Dial opening as a fraction of the diameter, by bezel type: a dive insert leaves the
# least dial showing.
_DIAL_OPENING: dict[BezelType, float] = {
    "none": 0.88,
    "smooth": 0.82,
    "fluted": 0.8,
    "rotating_insert": 0.74,
    "other": 0.8,
}

_CASE_COLOUR: dict[CaseMaterial, ColourName] = {
    "steel": "silver",
    "titanium": "grey",
    "gold": "gold",
    "ceramic": "black",
    "resin": "black",
    "bronze": "brown",
    "other": "silver",
}
Finish = Literal["polished", "brushed", "matte"]

_FINISH: dict[CaseMaterial, Finish] = {
    "steel": "brushed",
    "titanium": "brushed",
    "gold": "polished",
    "ceramic": "polished",
    "resin": "matte",
    "bronze": "brushed",
    "other": "brushed",
}
_STRAP_COLOUR: dict[StrapType, ColourName | None] = {
    "bracelet": None,  # the case colour
    "leather": "brown",
    "rubber": "black",
    "fabric": "grey",
    "other": "black",
}
_LIGHT_DIALS: frozenset[ColourName] = frozenset(
    {"white", "silver", "cream", "champagne", "yellow", "pink", "gold"}
)


@dataclass(frozen=True)
class Dimensions:
    """Lengths in millimetres from a measurement or a cited source; None when unknown."""

    case_shape: CaseShape
    case_diameter_mm: float
    case_length_mm: float | None = None
    bezel_diameter_mm: float | None = None
    dial_opening_mm: float | None = None
    lug_to_lug_mm: float | None = None
    thickness_mm: float | None = None
    lug_width_mm: float | None = None
    crown_position: int | None = None


@dataclass(frozen=True)
class Appearance:
    """What the watch looks like; None when unknown."""

    bezel_type: BezelType | None = None
    case_material: CaseMaterial | None = None
    case_colour: ColourName | None = None
    dial_colour: ColourName | None = None
    strap_type: StrapType | None = None


def build_spec(dims: Dimensions, look: Appearance | None = None) -> StandInSpec:
    """Build a complete stand-in from what is known, listing every dimension it assumed."""
    look = look or Appearance()
    assumed: list[str] = []

    def known_or(path: str, value: float | None, default: float) -> float:
        if value is not None:
            return value
        assumed.append(path)
        return round(default, 2)

    diameter = dims.case_diameter_mm
    if dims.case_shape == "round":
        length, squareness, taper = diameter, 2.0, 1.0
    else:
        squareness, taper, length_ratio = _SHAPE_OUTLINE[dims.case_shape]
        length = known_or("case.length_mm", dims.case_length_mm, diameter * length_ratio)
        assumed += ["case.squareness", "case.taper"]

    material: CaseMaterial = look.case_material or "steel"
    case_colour = PALETTE[look.case_colour or _CASE_COLOUR[material]]
    case = Case(
        shape=dims.case_shape,
        diameter_mm=diameter,
        length_mm=length,
        squareness=squareness,
        taper=taper,
        thickness_mm=known_or("case.thickness_mm", dims.thickness_mm, diameter * _THICKNESS),
        crystal_dome_mm=known_or("case.crystal_dome_mm", None, 0.0),
        material=material,
        finish=_FINISH[material],
        colour=case_colour,
    )

    bezel_type: BezelType = look.bezel_type or "smooth"
    dial_colour = PALETTE[look.dial_colour or "black"]
    if bezel_type == "none":
        bezel = Bezel(type="none", outer_mm=None, colour=None, insert_colour=None, markings="none")
    else:
        insert = bezel_type == "rotating_insert"
        bezel = Bezel(
            type=bezel_type,
            outer_mm=known_or("bezel.outer_mm", dims.bezel_diameter_mm, diameter),
            colour=case_colour,
            insert_colour=PALETTE["black"] if insert else None,
            markings="dive" if insert else "none",
        )

    light_dial = (look.dial_colour or "black") in _LIGHT_DIALS
    marker = PALETTE["black"] if light_dial else PALETTE["white"]
    opening_default = diameter * _DIAL_OPENING[bezel_type]
    dial = Dial(
        opening_mm=known_or("dial.opening_mm", dims.dial_opening_mm, opening_default),
        colour=dial_colour,
        index_style="baton",
        index_colour=marker,
        hands_colour=marker,
    )

    lug_width = known_or(
        "lugs.lug_width_mm", dims.lug_width_mm, 2 * round(diameter * _LUG_WIDTH / 2)
    )
    lugs = Lugs(
        lug_to_lug_mm=known_or(
            "lugs.lug_to_lug_mm",
            dims.lug_to_lug_mm,
            max(diameter * _LUG_TO_LUG, length * _LUG_TO_LUG_OF_LENGTH),
        ),
        lug_width_mm=lug_width,
        style="standard",
    )

    if dims.crown_position is None:
        assumed.append("crown.position")
    crown = Crown(
        position=dims.crown_position or 3,
        diameter_mm=known_or("crown.diameter_mm", None, diameter * _CROWN_DIAMETER),
        length_mm=known_or("crown.length_mm", None, _CROWN_LENGTH_MM),
        guards=False,
    )

    strap_type: StrapType = look.strap_type or "leather"
    strap_colour = _STRAP_COLOUR[strap_type]
    strap = Strap(
        type=strap_type,
        colour=PALETTE[strap_colour] if strap_colour else case_colour,
        width_at_buckle_mm=known_or("strap.width_at_buckle_mm", None, max(lug_width - 2, 8.0)),
    )

    return StandInSpec(
        spec_version=1,
        case=case,
        bezel=bezel,
        dial=dial,
        lugs=lugs,
        crown=crown,
        strap=strap,
        assumed=assumed,
    )


def check_spec(spec: StandInSpec) -> list[str]:
    """Every way the spec breaks a rule the schema can't express; empty when valid."""
    problems: list[str] = []
    case, bezel, dial, lugs = spec.case, spec.bezel, spec.dial, spec.lugs

    unknown = sorted(set(spec.assumed) - ASSUMABLE)
    if unknown:
        problems.append(f"assumed lists fields that can't be assumed: {', '.join(unknown)}")
    if len(set(spec.assumed)) != len(spec.assumed):
        problems.append("assumed lists a field twice")

    if case.shape == "round" and (
        case.length_mm != case.diameter_mm or case.squareness != 2 or case.taper != 1
    ):
        problems.append("a round case has length = diameter, squareness 2 and taper 1")
    if case.crystal_dome_mm >= case.thickness_mm:
        problems.append("the crystal's dome is taller than the whole case")

    if bezel.type == "none":
        if bezel.outer_mm is not None or bezel.colour is not None:
            problems.append("a watch without a bezel has no bezel width or colour")
    elif bezel.outer_mm is None or bezel.colour is None:
        problems.append(f"a {bezel.type} bezel needs its width and colour")
    if (bezel.insert_colour is not None) != (bezel.type == "rotating_insert"):
        problems.append("only a rotating bezel has an insert colour, and it always has one")
    if bezel.type == "none" and bezel.markings != "none":
        problems.append("a watch without a bezel has no bezel markings")
    if bezel.outer_mm is not None and bezel.outer_mm > case.diameter_mm + 3:
        problems.append("the bezel is more than 3 mm wider than the case")

    if dial.opening_mm >= case.diameter_mm:
        problems.append("the dial opening is not smaller than the case")
    if bezel.outer_mm is not None and dial.opening_mm >= bezel.outer_mm:
        problems.append("the dial opening is not smaller than the bezel")

    if lugs.lug_to_lug_mm < case.length_mm:
        problems.append("lug-to-lug is shorter than the case")
    if lugs.lug_width_mm >= case.diameter_mm:
        problems.append("the lugs are as wide as the case")
    if spec.strap.width_at_buckle_mm > lugs.lug_width_mm:
        problems.append("the strap is wider at the buckle than between the lugs")
    return problems
