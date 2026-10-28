"""The JSON Schemas and the generated Pydantic contracts agree on what is valid."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, get_args

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ValidationError
from referencing import Registry, Resource

from lugtolug_core import standin, vocab
from lugtolug_core.contracts import CatalogueEntry, ImageAnnotation, StandInSpec
from lugtolug_core.standin import Appearance, Dimensions, build_spec

SCHEMAS = Path(__file__).resolve().parents[3] / "data" / "schemas"


def _schema(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    return loaded


REGISTRY: Registry[Any] = Registry().with_resources(
    (path.name, Resource.from_contents(_schema(path.name)))
    for path in SCHEMAS.glob("*.schema.json")
)


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(
        _schema(name), registry=REGISTRY, format_checker=Draft202012Validator.FORMAT_CHECKER
    )


def test_every_schema_is_valid_json_schema() -> None:
    names = sorted(p.name for p in SCHEMAS.glob("*.schema.json"))
    assert names == [
        "annotation.schema.json",
        "catalogue-entry.schema.json",
        "common.schema.json",
        "stand-in-spec.schema.json",
    ]
    for name in names:
        Draft202012Validator.check_schema(_schema(name))


@pytest.mark.parametrize(
    ("alias", "definition"),
    [
        (vocab.CaseShape, "CaseShape"),
        (vocab.CaseMaterial, "CaseMaterial"),
        (vocab.BezelType, "BezelType"),
        (vocab.StrapType, "StrapType"),
        (vocab.ColourName, "ColourName"),
    ],
)
def test_vocabularies_match_the_schema(alias: object, definition: str) -> None:
    assert list(get_args(alias)) == _schema("common.schema.json")["$defs"][definition]["enum"]


def test_finish_matches_the_schema() -> None:
    finish = _schema("stand-in-spec.schema.json")["$defs"]["Case"]["properties"]["finish"]
    assert list(get_args(standin.Finish)) == finish["enum"]


# ---------------------------------------------------------------------------------------
# Examples that both validators must accept, and changes that both must reject.


def _spec() -> dict[str, Any]:
    spec = build_spec(
        Dimensions(case_shape="round", case_diameter_mm=40, lug_to_lug_mm=47.5),
        Appearance(bezel_type="rotating_insert", dial_colour="blue", strap_type="bracelet"),
    )
    return spec.model_dump(mode="json")


def _entry() -> dict[str, Any]:
    cited = {"value_mm": 40.0, "tolerance_mm": 0.5, "source": "S0001"}
    return {
        "entry_version": 1,
        "id": "examplebrand-1234-56",
        "brand": "Examplebrand",
        "model": "Diver",
        "reference": "1234.56",
        "aliases": ["The Example"],
        "source": "S0001",
        "case_shape": {"value": "round", "source": "S0001"},
        "case_diameter_mm": cited,
        "case_length_mm": None,
        "bezel_diameter_mm": None,
        "dial_opening_mm": None,
        "lug_to_lug_mm": {"value_mm": 47.5, "tolerance_mm": 0.25, "source": "S0002"},
        "thickness_mm": {"value_mm": 12.0, "tolerance_mm": 0.5, "source": "S0001"},
        "lug_width_mm": {"value_mm": 20.0, "tolerance_mm": 0.5, "source": "S0001"},
        "bezel_type": {"value": "rotating_insert", "source": "S0001"},
        "case_material": {"value": "steel", "source": "S0001"},
        "case_colour": {"value": "silver", "source": "S0001"},
        "dial_colour": {"value": "black", "source": "S0001"},
        "strap_type": {"value": "bracelet", "source": "S0001"},
        "crown_position": {"value": 3, "source": "S0001"},
        "sources": [
            {
                "id": "S0001",
                "kind": "manufacturer",
                "publisher": "Examplebrand",
                "title": "Diver 1234.56",
                "url": "https://example.com/watches/1234-56",
                "accessed": "2026-10-28",
                "archived_url": None,
            },
            {
                "id": "S0002",
                "kind": "review",
                "publisher": "Example Reviews",
                "title": "Diver review",
                "url": "https://example.org/review",
                "accessed": "2026-10-28",
                "archived_url": "https://web.archive.org/web/2026/https://example.org/review",
            },
        ],
    }


def _annotation() -> dict[str, Any]:
    provenance = {
        "method": "model_proposed_person_corrected",
        "labeller": "P01",
        "proposer": "edge-ellipse 0.1.0",
        "tool": "lugtolug-tools 0.1.0",
        "created": "2026-11-03T10:12:00+05:30",
    }
    ring = [{"x": 1000 + 200 * i, "y": 800 + (i % 2) * 150} for i in range(6)]
    return {
        "annotation_version": 1,
        "image_id": "P01_S01_T00-DAY_W01_1",
        "image_sha256": "0" * 64,
        "width": 4080,
        "height": 3072,
        "case_outline": {"points": ring, "provenance": provenance},
        "dial_outline": None,
        "wrist_edges": {
            "radial": [{"x": 0, "y": 500}, {"x": 4079, "y": 520}],
            "ulnar": [{"x": 0, "y": 2400}, {"x": 4079, "y": 2380}],
            "provenance": {**provenance, "method": "person_drawn", "proposer": None},
        },
        "identity": {
            "watch_id": "W01",
            "provenance": {**provenance, "method": "session_sheet", "labeller": None},
        },
        "flags": {
            "blurred": False,
            "glare": False,
            "occluded": False,
            "strap_moved": False,
            "unusable": False,
            "note": "",
        },
    }


Contract = tuple[str, type[BaseModel], Callable[[], dict[str, Any]]]
CONTRACTS: list[Contract] = [
    ("stand-in-spec.schema.json", StandInSpec, _spec),
    ("catalogue-entry.schema.json", CatalogueEntry, _entry),
    ("annotation.schema.json", ImageAnnotation, _annotation),
]


@pytest.mark.parametrize(("schema", "model", "example"), CONTRACTS)
def test_examples_are_valid_in_both(
    schema: str, model: type[BaseModel], example: Callable[[], dict[str, Any]]
) -> None:
    _validator(schema).validate(example())
    parsed = model.model_validate(example())
    assert parsed.model_dump(mode="json", exclude_none=False) == example()


def _set(doc: dict[str, Any], path: str, value: object) -> dict[str, Any]:
    changed = copy.deepcopy(doc)
    *parents, last = path.split(".")
    node: Any = changed
    for key in parents:
        node = node[int(key)] if isinstance(node, list) else node[key]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value
    return changed


BROKEN = [
    ("stand-in-spec.schema.json", StandInSpec, _spec, "spec_version", 2),
    ("stand-in-spec.schema.json", StandInSpec, _spec, "case.diameter_mm", -1),
    ("stand-in-spec.schema.json", StandInSpec, _spec, "case.shape", "oval"),
    ("stand-in-spec.schema.json", StandInSpec, _spec, "case.colour", "#ABCDEF"),
    ("stand-in-spec.schema.json", StandInSpec, _spec, "case.squareness", 1.5),
    ("stand-in-spec.schema.json", StandInSpec, _spec, "case.extra", 1),
    ("stand-in-spec.schema.json", StandInSpec, _spec, "crown.position", 13),
    ("stand-in-spec.schema.json", StandInSpec, _spec, "bezel.markings", "logo"),
    ("catalogue-entry.schema.json", CatalogueEntry, _entry, "id", "Has Spaces"),
    ("catalogue-entry.schema.json", CatalogueEntry, _entry, "source", "1"),
    ("catalogue-entry.schema.json", CatalogueEntry, _entry, "case_diameter_mm.value_mm", 0),
    ("catalogue-entry.schema.json", CatalogueEntry, _entry, "dial_colour.value", "teal"),
    ("catalogue-entry.schema.json", CatalogueEntry, _entry, "sources", []),
    ("catalogue-entry.schema.json", CatalogueEntry, _entry, "sources.0.accessed", "28/10/2026"),
    ("annotation.schema.json", ImageAnnotation, _annotation, "image_sha256", "abc"),
    ("annotation.schema.json", ImageAnnotation, _annotation, "case_outline.points", []),
    ("annotation.schema.json", ImageAnnotation, _annotation, "identity.watch_id", "X1"),
    ("annotation.schema.json", ImageAnnotation, _annotation, "flags.blurred", "yes"),
    (
        "annotation.schema.json",
        ImageAnnotation,
        _annotation,
        "case_outline.provenance.method",
        "guessed",
    ),
    (
        "annotation.schema.json",
        ImageAnnotation,
        _annotation,
        "wrist_edges.provenance.labeller",
        "someone",
    ),
]


@pytest.mark.parametrize(("schema", "model", "example", "path", "value"), BROKEN)
def test_broken_examples_are_rejected_by_both(
    schema: str,
    model: type[BaseModel],
    example: Callable[[], dict[str, Any]],
    path: str,
    value: object,
) -> None:
    broken = _set(example(), path, value)
    assert not _validator(schema).is_valid(broken)
    with pytest.raises(ValidationError):
        model.model_validate(broken)


def test_duplicate_assumed_fields_are_caught_by_the_schema_and_the_rules() -> None:
    # JSON Schema's uniqueItems has no Pydantic equivalent for lists; check_spec covers it.
    spec = _spec()
    spec["assumed"] = ["case.thickness_mm", "case.thickness_mm"]
    assert not _validator("stand-in-spec.schema.json").is_valid(spec)
    assert "assumed lists a field twice" in standin.check_spec(StandInSpec.model_validate(spec))
