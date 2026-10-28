"""build_spec() fills what's unknown and says so; check_spec() enforces the rules."""

from __future__ import annotations

from typing import Any, get_args

import pytest

from lugtolug_core.contracts.stand_in import StandInSpec
from lugtolug_core.standin import ASSUMABLE, Appearance, Dimensions, build_spec, check_spec
from lugtolug_core.vocab import BezelType, CaseShape

# Never published by any source, so a stand-in always assumes them.
ALWAYS_ASSUMED = {
    "case.crystal_dome_mm",
    "crown.diameter_mm",
    "crown.length_mm",
    "strap.width_at_buckle_mm",
}


def test_a_fully_known_round_watch_assumes_only_what_is_never_published() -> None:
    spec = build_spec(
        Dimensions(
            case_shape="round",
            case_diameter_mm=40,
            bezel_diameter_mm=40.5,
            dial_opening_mm=30.5,
            lug_to_lug_mm=47.6,
            thickness_mm=12.5,
            lug_width_mm=20,
            crown_position=3,
        ),
        Appearance(bezel_type="rotating_insert", case_material="steel", dial_colour="black"),
    )
    assert set(spec.assumed) == ALWAYS_ASSUMED
    assert check_spec(spec) == []
    assert spec.case.length_mm == spec.case.diameter_mm == 40
    assert (spec.case.squareness, spec.case.taper) == (2, 1)
    assert spec.lugs.lug_to_lug_mm == 47.6
    assert spec.bezel.insert_colour is not None
    assert spec.bezel.markings == "dive"


def test_unknown_dimensions_come_from_typical_proportions_and_are_listed() -> None:
    spec = build_spec(Dimensions(case_shape="round", case_diameter_mm=40))
    assert set(spec.assumed) == ALWAYS_ASSUMED | {
        "case.thickness_mm",
        "bezel.outer_mm",
        "dial.opening_mm",
        "lugs.lug_to_lug_mm",
        "lugs.lug_width_mm",
        "crown.position",
    }
    assert spec.case.thickness_mm == 12
    assert spec.lugs.lug_to_lug_mm == 48
    assert spec.lugs.lug_width_mm == 20
    assert spec.crown.position == 3
    assert check_spec(spec) == []


def test_non_round_outlines_are_always_assumed() -> None:
    spec = build_spec(Dimensions(case_shape="tonneau", case_diameter_mm=36))
    assert {"case.length_mm", "case.squareness", "case.taper"} <= set(spec.assumed)
    assert spec.case.taper < 1
    assert spec.case.length_mm > spec.case.diameter_mm
    assert check_spec(spec) == []

    measured = build_spec(Dimensions(case_shape="square", case_diameter_mm=25.5, case_length_mm=33))
    assert "case.length_mm" not in measured.assumed
    assert measured.case.length_mm == 33


def test_a_watch_without_a_bezel_has_no_bezel_dimensions() -> None:
    spec = build_spec(Dimensions(case_shape="round", case_diameter_mm=38), Appearance("none"))
    assert spec.bezel.outer_mm is None
    assert spec.bezel.colour is None
    assert "bezel.outer_mm" not in spec.assumed
    assert check_spec(spec) == []


@pytest.mark.parametrize("shape", get_args(CaseShape))
@pytest.mark.parametrize("bezel", get_args(BezelType))
@pytest.mark.parametrize("diameter", [24.0, 34.0, 40.0, 46.0, 55.0])
def test_every_built_spec_passes_the_rules(
    shape: CaseShape, bezel: BezelType, diameter: float
) -> None:
    spec = build_spec(Dimensions(case_shape=shape, case_diameter_mm=diameter), Appearance(bezel))
    assert check_spec(spec) == []
    assert set(spec.assumed) <= ASSUMABLE


def _change(spec: StandInSpec, section: str, **fields: Any) -> StandInSpec:
    part = getattr(spec, section)
    return spec.model_copy(update={section: part.model_copy(update=fields)})


@pytest.fixture
def spec() -> StandInSpec:
    return build_spec(
        Dimensions(case_shape="round", case_diameter_mm=40, lug_to_lug_mm=48),
        Appearance(bezel_type="rotating_insert"),
    )


@pytest.mark.parametrize(
    ("section", "fields", "problem"),
    [
        ("case", {"length_mm": 42.0}, "a round case has"),
        ("case", {"crystal_dome_mm": 4.0, "thickness_mm": 3.5}, "dome is taller"),
        ("bezel", {"outer_mm": None}, "needs its width and colour"),
        ("bezel", {"insert_colour": None}, "only a rotating bezel has an insert colour"),
        ("bezel", {"outer_mm": 44.0}, "more than 3 mm wider"),
        ("dial", {"opening_mm": 40.0}, "not smaller than the case"),
        ("lugs", {"lug_to_lug_mm": 39.0}, "shorter than the case"),
        ("lugs", {"lug_width_mm": 40.0}, "as wide as the case"),
        ("strap", {"width_at_buckle_mm": 24.0}, "wider at the buckle"),
    ],
)
def test_each_rule_catches_its_mistake(
    spec: StandInSpec, section: str, fields: dict[str, Any], problem: str
) -> None:
    assert check_spec(spec) == []
    problems = check_spec(_change(spec, section, **fields))
    assert any(problem in p for p in problems), problems


def test_a_bezel_less_watch_cannot_have_bezel_markings(spec: StandInSpec) -> None:
    broken = _change(
        spec, "bezel", type="none", outer_mm=None, colour=None, insert_colour=None, markings="dive"
    )
    assert any("no bezel markings" in p for p in check_spec(broken))


def test_assumed_paths_must_be_assumable(spec: StandInSpec) -> None:
    broken = spec.model_copy(update={"assumed": ["case.diameter_mm", "dial.colour"]})
    assert any("can't be assumed: case.diameter_mm, dial.colour" in p for p in check_spec(broken))
