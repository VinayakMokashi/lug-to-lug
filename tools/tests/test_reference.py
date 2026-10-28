"""reference.csv is built from the three rounds, and never carries a watch's identity."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from lugtolug_core.catalogue import ReferenceWatch, load_reference
from lugtolug_tools.reference import (
    MEASUREMENT_COLUMNS,
    build_reference,
    reference_csv,
    repeatability,
)

LIST_COLUMNS = (
    "watch_id",
    "brand",
    "model",
    "reference_number",
    "case_shape",
    "bezel_type",
    "case_material",
    "case_colour",
    "dial_colour",
    "strap_type",
    "notes",
)
DIVER = {
    "watch_id": "W01",
    "brand": "Examplebrand",
    "model": "Diver",
    "reference_number": "1234.56",
    "case_shape": "round",
    "bezel_type": "rotating_insert",
    "case_material": "steel",
    "case_colour": "silver",
    "dial_colour": "black",
    "strap_type": "bracelet",
}
READINGS: dict[str, tuple[str, ...]] = {
    "case_diameter_mm": ("40.02", "39.98", "40.05"),
    "bezel_diameter_mm": ("40.40", "40.44", "40.41"),
    "dial_opening_mm": ("30.10", "30.20", "30.15"),
    "lug_to_lug_mm": ("47.60", "47.70", "47.62"),
    "thickness_mm": ("12.30", "12.36", "12.31"),
    "lug_width_mm": ("20.00", "20.02", "20.01"),
}


def _write(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> Path:
    lines = [",".join(columns)] + [",".join(r.get(c, "") for c in columns) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _rounds(
    watch: str = "W01", readings: Mapping[str, tuple[str, ...]] = READINGS
) -> list[dict[str, str]]:
    rounds = len(next(iter(readings.values())))
    return [
        {"round": str(r + 1), "watch_id": watch, **{f: v[r] for f, v in readings.items() if v[r]}}
        for r in range(rounds)
    ]


def _build(
    tmp_path: Path, rows: list[dict[str, str]], looks: list[dict[str, str]] | None = None
) -> tuple[list[ReferenceWatch], list[str]]:
    measurements = _write(tmp_path / "watch-measurements.csv", MEASUREMENT_COLUMNS, rows)
    watch_list = _write(tmp_path / "watch-list.csv", LIST_COLUMNS, looks or [DIVER])
    return build_reference(measurements, watch_list)


def test_medians_and_ranges(tmp_path: Path) -> None:
    unmeasured = {"round": "1", "watch_id": "W02"}
    watches, problems = _build(tmp_path, [*_rounds(), unmeasured])
    assert problems == []
    (watch,) = watches
    assert watch.case_diameter_mm.median_mm == 40.02
    assert watch.case_diameter_mm.range_mm == 0.07
    assert watch.lug_to_lug_mm is not None
    assert watch.lug_to_lug_mm.median_mm == 47.62
    assert watch.case_length_mm is None
    assert watch.rounds == 3


def test_the_file_has_no_identity_and_loads_back(tmp_path: Path) -> None:
    watches, _ = _build(tmp_path, _rounds())
    text = reference_csv(watches)
    assert "Examplebrand" not in text
    assert "Diver" not in text
    assert "1234.56" not in text
    path = tmp_path / "reference.csv"
    path.write_text(text, encoding="utf-8")
    assert load_reference(path) == watches


def test_a_dimension_measured_in_some_rounds_only(tmp_path: Path) -> None:
    readings = {**READINGS, "bezel_diameter_mm": ("40.40", "", "40.41")}
    _, problems = _build(tmp_path, _rounds(readings=readings))
    assert (
        "W01: bezel_diameter_mm is measured in rounds [1, 3] but the watch in rounds [1, 2, 3]"
        in problems
    )


def test_three_rounds_are_needed(tmp_path: Path) -> None:
    two = {f: v[:2] for f, v in READINGS.items()}
    _, problems = _build(tmp_path, _rounds(readings=two))
    assert "W01: measured in 2 round(s); three are needed" in problems


def test_readings_that_break_a_rule_are_caught(tmp_path: Path) -> None:
    # A dial opening wider than the case is a misread or a typo, not a watch.
    readings = {**READINGS, "dial_opening_mm": ("41.10", "41.20", "41.15")}
    _, problems = _build(tmp_path, _rounds(readings=readings))
    expected = "the dial opening is not smaller than the case (check the readings)"
    assert any(expected in p for p in problems)


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"case_shape": "oval"}, "case_shape 'oval' is not one of round, cushion"),
        ({"dial_colour": "Black"}, "dial_colour 'Black' is not one of black"),
        ({"strap_type": ""}, "strap_type '' is not one of"),
    ],
)
def test_appearance_uses_the_listed_words(
    tmp_path: Path, change: dict[str, str], problem: str
) -> None:
    _, problems = _build(tmp_path, _rounds(), [{**DIVER, **change}])
    assert any(problem in p for p in problems), problems


def test_a_round_case_has_no_case_length(tmp_path: Path) -> None:
    readings = {**READINGS, "case_length_mm": ("44.0", "44.1", "44.0")}
    _, problems = _build(tmp_path, _rounds(readings=readings))
    assert "W01: a round case has no separate case length" in problems


def test_odd_readings_are_reported(tmp_path: Path) -> None:
    rows = _rounds()
    rows[0]["thickness_mm"] = "12.3.1"
    rows[1]["lug_width_mm"] = "200"
    rows.append({"round": "x", "watch_id": "W01", "case_diameter_mm": "40"})
    rows.append({**rows[2]})
    _, problems = _build(tmp_path, rows)
    text = "\n".join(problems)
    assert "thickness_mm '12.3.1' is not a number" in text
    assert "lug_width_mm 200.0 mm is outside 0-100 mm" in text
    assert "round must be 1, 2 or 3" in text
    assert "has two readings in round 3" in text


def test_a_comma_inside_a_value_is_reported(tmp_path: Path) -> None:
    path = _write(tmp_path / "watch-measurements.csv", MEASUREMENT_COLUMNS, _rounds())
    # Twelve point three typed with a decimal comma, which a CSV file reads as two cells.
    with path.open("a", encoding="utf-8") as f:
        f.write("1,W02,40,,,,,,12,3,\n")
    watch_list = _write(tmp_path / "watch-list.csv", LIST_COLUMNS, [DIVER])
    _, problems = build_reference(path, watch_list)
    assert "watch-measurements.csv line 5: more cells than the header" in problems[0]


def test_a_measured_watch_must_be_on_the_list(tmp_path: Path) -> None:
    _, problems = _build(tmp_path, _rounds("W07"))
    assert "W07: measured but not in watch-list.csv" in problems


def test_repeatability_summarises_the_spread(tmp_path: Path) -> None:
    second = {f: tuple(f"{float(v) + 1:.2f}" for v in vs) for f, vs in READINGS.items()}
    second["case_diameter_mm"] = ("41.00", "41.30", "41.10")
    rows = _rounds() + _rounds("W02", second)
    watches, problems = _build(tmp_path, rows, [DIVER, {**DIVER, "watch_id": "W02"}])
    assert problems == []
    diameter = next(s for s in repeatability(watches) if s.field == "case_diameter_mm")
    assert (diameter.watches, diameter.largest_range_mm, diameter.worst_watch) == (2, 0.3, "W02")
    assert diameter.median_range_mm == pytest.approx((0.07 + 0.3) / 2)
