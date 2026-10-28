"""The session plan: one row per placement, written before any photo is taken.

The plan is the only record of what each photo shows. The ingest matches photos to its
rows in order and refuses when the photos and the plan disagree, so the plan has to be
right: if a placement got more or fewer photos than planned, its `shots` cell is
corrected before ingesting.

A session is one block: one person (none for product photos), one camera tilt and one
light, photographed in one folder.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

COLUMNS = (
    "session_id",
    "date",
    "person_id",
    "block",
    "surface",
    "seq",
    "watch_id",
    "shots",
    "reseat",
    "notes",
)
SESSION = re.compile(r"^S[0-9]{2}$")
PERSON = re.compile(r"^P[0-9]{2}$")
WATCH = re.compile(r"^W[0-9]{2,3}$")
UNCHOSEN = "W??"
# Wrist blocks are a tilt and a light; handheld photos have no fixed tilt; product
# photos have no person.
WRIST_BLOCK = re.compile(r"^(?:T00|T20|T40|HAND)-(?:DAY|WARM|MIX)$")
PRODUCT_BLOCK = re.compile(r"^PRODUCT-(?:TOP|SIDE)$")
SURFACES = frozenset({"backdrop", "desk", "fabric"})

# A row with more cells than its header: usually a decimal comma, as in 12,3 for 12.3.
EXTRA_CELLS = "more cells than the header (a comma inside a value?)"


class PlanError(Exception):
    """The plan breaks one or more rules; `problems` lists them all."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__(f"{len(problems)} problem(s) in the plan:\n" + "\n".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class Placement:
    """One placement: a watch put on (or laid down) once, and photographed `shots` times."""

    session_id: str
    date: date | None
    person_id: str  # empty for product photos
    block: str
    surface: str
    seq: int
    watch_id: str
    shots: int
    reseat: bool
    notes: str

    def image_id(self, shot: int) -> str:
        """The benchmark name of this placement's photo number `shot` (from 1).

        The placement number keeps a re-seat check's four placements of the same watch
        apart: P01_S03_T20-DAY_07_W12_1.
        """
        parts = [self.person_id] if self.person_id else []
        parts += [self.session_id, self.block, f"{self.seq:02d}", self.watch_id, str(shot)]
        return "_".join(parts)

    @property
    def product(self) -> bool:
        return PRODUCT_BLOCK.match(self.block) is not None


def _placement(row: dict[str, str], where: str, problems: list[str]) -> Placement | None:
    found = len(problems)
    session_id, person, block = row["session_id"], row["person_id"], row["block"]
    if not SESSION.match(session_id):
        problems.append(f"{where}: session_id {session_id!r} is not like S01")
    product = PRODUCT_BLOCK.match(block) is not None
    if not product and not WRIST_BLOCK.match(block):
        problems.append(f"{where}: block {block!r} is not like T20-DAY, HAND-MIX or PRODUCT-TOP")
    if product and person:
        problems.append(f"{where}: product photos have no person")
    if not product and not PERSON.match(person):
        problems.append(f"{where}: person_id {person!r} is not like P01")
    if row["surface"] not in SURFACES:
        problems.append(f"{where}: surface must be one of {', '.join(sorted(SURFACES))}")
    if row["watch_id"] != UNCHOSEN and not WATCH.match(row["watch_id"]):
        problems.append(f"{where}: watch_id {row['watch_id']!r} is not like W01")
    if row["reseat"] not in ("yes", ""):
        problems.append(f"{where}: reseat is 'yes' or empty")
    seq = int(row["seq"]) if row["seq"].isdigit() else 0
    if seq < 1:
        problems.append(f"{where}: seq must be a whole number from 1")
    shots = int(row["shots"]) if row["shots"].isdigit() else -1
    if shots < 0:
        problems.append(f"{where}: shots must be a whole number (0 if the placement was skipped)")
    day = None
    if row["date"]:
        try:
            day = date.fromisoformat(row["date"])
        except ValueError:
            problems.append(f"{where}: date {row['date']!r} is not YYYY-MM-DD")
    if len(problems) > found:
        return None
    return Placement(
        session_id=session_id,
        date=day,
        person_id=person,
        block=block,
        surface=row["surface"],
        seq=seq,
        watch_id=row["watch_id"],
        shots=shots,
        reseat=row["reseat"] == "yes",
        notes=row["notes"],
    )


def read_plan(path: Path) -> dict[str, list[Placement]]:
    """Every session's placements in plan order, after checking the whole plan.

    Raises PlanError listing every problem found.
    """
    problems: list[str] = []
    sessions: dict[str, list[Placement]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise PlanError([f"{path.name}: the header must be {','.join(COLUMNS)}"])
        for line, raw in enumerate(reader, start=2):
            if None in raw:
                problems.append(f"{path.name} line {line}: {EXTRA_CELLS}")
                continue
            row = {key: (value or "").strip() for key, value in raw.items()}
            placement = _placement(row, f"{path.name} line {line}", problems)
            if placement is not None:
                sessions.setdefault(placement.session_id, []).append(placement)

    for session_id, placements in sessions.items():
        first = placements[0]
        if any(p.person_id != first.person_id or p.block != first.block for p in placements):
            problems.append(f"{session_id}: one session is one person and one block")
        if not first.block.startswith("HAND") and len({p.surface for p in placements}) > 1:
            problems.append(f"{session_id}: only handheld sessions change surface")
        if [p.seq for p in placements] != list(range(1, len(placements) + 1)):
            problems.append(f"{session_id}: seq must run 1, 2, 3, ... in order")
    if problems:
        raise PlanError(problems)
    return sessions
