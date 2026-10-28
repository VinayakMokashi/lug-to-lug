"""The session plan is read whole and every broken rule is reported."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from lugtolug_tools.plan import PlanError, read_plan
from lugtolug_tools.testing import block_rows, write_plan


def test_a_block_reads_in_order(tmp_path: Path) -> None:
    plan = read_plan(write_plan(tmp_path / "plan.csv", block_rows()))
    (s03,) = plan.values()
    assert [p.watch_id for p in s03] == ["W01", "W01", "W02", "W03", "W01", "W01"]
    assert [p.reseat for p in s03] == [True, True, False, False, True, True]
    assert s03[0].date == date(2026, 11, 2)
    assert s03[2].image_id(1) == "P01_S03_T20-DAY_03_W02_1"
    # The placement number keeps the re-seat photos of the first watch apart.
    assert len({p.image_id(1) for p in s03}) == len(s03)


def test_product_photos_have_no_person(tmp_path: Path) -> None:
    rows = [
        {
            "session_id": "S15",
            "block": "PRODUCT-TOP",
            "surface": "backdrop",
            "seq": str(i + 1),
            "watch_id": f"W0{i + 1}",
            "shots": "2",
        }
        for i in range(3)
    ]
    (s15,) = read_plan(write_plan(tmp_path / "plan.csv", rows)).values()
    assert s15[0].product
    assert s15[0].image_id(2) == "S15_PRODUCT-TOP_01_W01_2"


def test_handheld_sessions_may_change_surface(tmp_path: Path) -> None:
    rows = block_rows("S14", block="HAND-DAY")
    rows[-1]["surface"] = "fabric"
    assert read_plan(write_plan(tmp_path / "plan.csv", rows))
    rows = block_rows("S01", block="T00-DAY")
    rows[-1]["surface"] = "fabric"
    with pytest.raises(PlanError, match="only handheld sessions change surface"):
        read_plan(write_plan(tmp_path / "plan.csv", rows))


def test_an_unchosen_watch_is_allowed_in_the_plan(tmp_path: Path) -> None:
    (s10,) = read_plan(write_plan(tmp_path / "plan.csv", block_rows("S10", ("W??",)))).values()
    assert s10[0].watch_id == "W??"


def test_every_problem_is_reported(tmp_path: Path) -> None:
    rows = block_rows()
    rows[0].update(session_id="S3")
    rows[1].update(block="T30-DAY")
    rows[2].update(person_id="Someone")
    rows[3].update(watch_id="12")
    rows[4].update(shots="two", reseat="y")
    rows[5].update(date="02/11/2026", surface="table")
    rows.append({**block_rows()[0], "seq": "9"})
    rows.append({**block_rows("S15")[0], "person_id": "P01", "block": "PRODUCT-SIDE"})
    with pytest.raises(PlanError) as caught:
        read_plan(write_plan(tmp_path / "plan.csv", rows))
    problems = "\n".join(caught.value.problems)
    for expected in [
        "session_id 'S3' is not like S01",
        "block 'T30-DAY' is not like",
        "person_id 'Someone' is not like P01",
        "watch_id '12' is not like W01",
        "shots must be a whole number",
        "reseat is 'yes' or empty",
        "date '02/11/2026' is not YYYY-MM-DD",
        "surface must be one of",
        "product photos have no person",
    ]:
        assert expected in problems


def test_seq_runs_in_order(tmp_path: Path) -> None:
    rows = block_rows()
    rows[2]["seq"], rows[3]["seq"] = rows[3]["seq"], rows[2]["seq"]
    with pytest.raises(PlanError, match=r"seq must run 1, 2, 3"):
        read_plan(write_plan(tmp_path / "plan.csv", rows))


def test_one_session_is_one_person_and_one_block(tmp_path: Path) -> None:
    rows = block_rows()
    rows[3]["person_id"] = "P02"
    with pytest.raises(PlanError, match="one session is one person and one block"):
        read_plan(write_plan(tmp_path / "plan.csv", rows))


def test_the_header_is_checked(tmp_path: Path) -> None:
    path = tmp_path / "plan.csv"
    path.write_text("session,watch\nS01,W01\n", encoding="utf-8")
    with pytest.raises(PlanError, match="the header must be"):
        read_plan(path)
