"""The private sheets read the same however a spreadsheet program saved them."""

from __future__ import annotations

from pathlib import Path

import pytest

from lugtolug_tools import sheets
from lugtolug_tools.plan import read_plan
from lugtolug_tools.reference import MEASUREMENT_COLUMNS, build_reference
from lugtolug_tools.testing import block_rows, write_plan

BOM = b"\xef\xbb\xbf"


def test_a_byte_order_mark_stays_out_of_the_first_column(tmp_path: Path) -> None:
    path = tmp_path / "sheet.csv"
    path.write_bytes(BOM + b"watch_id,brand\nW01,Oris\n")
    assert sheets.header(path) == ("watch_id", "brand")
    assert sheets.rows(path, []) == [(2, {"watch_id": "W01", "brand": "Oris"})]


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "cp1252"])
def test_an_accent_survives_every_way_of_saving(tmp_path: Path, encoding: str) -> None:
    path = tmp_path / "sheet.csv"
    path.write_bytes("watch_id,model\nW01,Éco\n".encode(encoding))
    assert sheets.rows(path, []) == [(2, {"watch_id": "W01", "model": "Éco"})]


def test_a_workbook_saved_with_a_csv_name_is_a_wrong_header_not_a_crash(tmp_path: Path) -> None:
    path = tmp_path / "sheet.csv"
    path.write_bytes(b"PK\x03\x04\x81\x8d\x8f\x90\x9d\xff")
    assert sheets.header(path) != ("watch_id",)


def test_empty_rows_are_skipped_and_lines_stay_true(tmp_path: Path) -> None:
    path = tmp_path / "sheet.csv"
    path.write_text("a,b\n1,2\n,\n,  \n3,4\n", encoding="utf-8")
    assert sheets.rows(path, []) == [(2, {"a": "1", "b": "2"}), (5, {"a": "3", "b": "4"})]


def test_extra_cells_are_reported_with_their_line(tmp_path: Path) -> None:
    path = tmp_path / "sheet.csv"
    path.write_text("a,b\n1,2\n3,4,5\n6,7\n", encoding="utf-8")
    problems: list[str] = []
    assert [line for line, _ in sheets.rows(path, problems)] == [2, 4]
    assert problems == [f"sheet.csv line 3: {sheets.EXTRA_CELLS}"]


def test_the_session_plan_reads_after_excel_saves_it(tmp_path: Path) -> None:
    path = write_plan(tmp_path / "plan.csv", block_rows())
    expected = read_plan(path)
    path.write_bytes(BOM + path.read_bytes().replace(b"\n", b"\r\n"))
    assert read_plan(path) == expected


def test_a_watch_list_saved_by_excel_builds_the_reference_table(tmp_path: Path) -> None:
    listed = tmp_path / "watch-list.csv"
    listed.write_bytes(BOM + b"watch_id,brand\r\nW01,Oris\r\n")
    measurements = tmp_path / "watch-measurements.csv"
    measurements.write_text(",".join(MEASUREMENT_COLUMNS) + "\n", encoding="utf-8")
    assert build_reference(measurements, listed) == ([], [])
