"""The watch list is checked row by row, before any watch has been measured."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from lugtolug_tools.cli import main
from lugtolug_tools.testing import block_rows, write_plan
from lugtolug_tools.watch_list import COLUMNS, ListReport, check_watch_list

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


def _write(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _check(tmp_path: Path, rows: list[dict[str, str]], planned: tuple[str, ...] = ()) -> ListReport:
    return check_watch_list(_write(tmp_path / "watch-list.csv", rows), planned)


def test_a_complete_row_and_a_blank_row(tmp_path: Path) -> None:
    report = _check(tmp_path, [DIVER, {"watch_id": "W02"}])
    assert report.ok
    assert (report.complete, report.blank) == (["W01"], ["W02"])
    assert report.render().splitlines()[0] == "1 watch(es) complete, 1 blank"


def test_a_list_that_passes_reference_is_still_checked(tmp_path: Path) -> None:
    # Nothing is measured yet, which is exactly when `poe reference` can't see these.
    report = _check(tmp_path, [{**DIVER, "case_shape": "Round", "strap_type": "steel"}])
    assert not report.ok
    assert report.complete == []
    text = "\n".join(report.problems)
    assert "W01: case_shape 'Round' is not one of round, cushion" in text
    assert "W01: strap_type 'steel' is not one of bracelet" in text


def test_the_report_never_names_a_watch(tmp_path: Path) -> None:
    second = {**DIVER, "watch_id": "W02", "dial_colour": "mauve"}
    text = _check(tmp_path, [DIVER, second, {**second, "watch_id": "W03"}]).render()
    for private in ("Examplebrand", "Diver", "1234.56"):
        assert private not in text


@pytest.mark.parametrize("column", ["brand", "model"])
def test_a_partly_filled_row_is_a_problem(tmp_path: Path, column: str) -> None:
    report = _check(tmp_path, [{**DIVER, column: ""}])
    assert report.problems == [f"W01: {column} is empty"]
    assert report.complete == []


def test_a_missing_reference_number_is_only_a_note(tmp_path: Path) -> None:
    report = _check(tmp_path, [{**DIVER, "reference_number": ""}])
    assert report.ok
    assert report.complete == ["W01"]
    assert report.notes == ["W01: no reference number"]


def test_ids_are_checked_and_unique(tmp_path: Path) -> None:
    report = _check(tmp_path, [DIVER, DIVER, {**DIVER, "watch_id": "12"}])
    assert report.problems == [
        "W01: listed twice",
        "watch-list.csv line 4: watch_id '12' is not like W01",
    ]


def test_the_same_model_twice_is_flagged_for_the_splits(tmp_path: Path) -> None:
    twin = {**DIVER, "watch_id": "W02", "brand": "EXAMPLEBRAND", "dial_colour": "blue"}
    report = _check(tmp_path, [DIVER, twin])
    assert report.ok
    assert report.notes == [
        "W01, W02: the same brand and model; if they share a case, split together"
    ]


def test_every_planned_watch_must_be_on_the_list(tmp_path: Path) -> None:
    report = _check(tmp_path, [DIVER, {**DIVER, "watch_id": "W36"}], ("W01", "W02"))
    assert report.problems == ["W02: in the session plan but not on the list"]
    assert "W36: not in the session plan" in report.notes


def test_a_changed_header_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "watch-list.csv"
    path.write_text("id,brand\nW01,Examplebrand\n", encoding="utf-8")
    report = check_watch_list(path)
    assert not report.ok
    assert "the header must be watch_id,brand" in report.problems[0]


def _private(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "sheets"
    folder.mkdir()
    write_plan(folder / "session-plan.csv", block_rows(watches=("W01",)))
    monkeypatch.setenv("LUGTOLUG_PRIVATE_DIR", str(tmp_path))
    return folder


def test_the_command_passes_a_good_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = _private(tmp_path, monkeypatch)
    _write(folder / "watch-list.csv", [DIVER])
    assert main(["watch-list"]) == 0
    assert "1 watch(es) complete, 0 blank" in capsys.readouterr().out


def test_the_command_fails_on_a_wrong_word(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = _private(tmp_path, monkeypatch)
    _write(folder / "watch-list.csv", [{**DIVER, "dial_colour": "Black"}])
    assert main(["watch-list"]) == 1
    assert "W01: dial_colour 'Black'" in capsys.readouterr().out
