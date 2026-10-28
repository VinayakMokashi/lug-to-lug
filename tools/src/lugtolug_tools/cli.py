"""The `lugtolug` command: `ingest S03`, `reference`, `phone-check <folder>`.

Paths default to the private store and work folder next to the repository
(lugtolug_tools.paths); nothing is written with --dry-run.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path

from lugtolug_tools import paths
from lugtolug_tools.ingest import DEFAULT_GAP_S, ingest
from lugtolug_tools.phone_check import run as check_phone
from lugtolug_tools.plan import PlanError, read_plan
from lugtolug_tools.reference import (
    MEASUREMENT_COLUMNS,
    build_reference,
    reference_csv,
    repeatability,
)


def _turn(text: str) -> tuple[str, int]:
    name, _, degrees = text.partition("=")
    if not name or not degrees.isdigit():
        raise argparse.ArgumentTypeError(f"{text!r} is not NAME=DEGREES")
    return name, int(degrees)


def _ingest(args: argparse.Namespace) -> int:
    private = paths.private_dir()
    try:
        plan = read_plan(private / "sheets" / "session-plan.csv")
    except PlanError as e:
        print(e, file=sys.stderr)
        return 1
    if args.session not in plan:
        print(f"{args.session} is not in the session plan", file=sys.stderr)
        return 1
    report = ingest(
        plan[args.session],
        private / "raw" / "sessions" / args.session,
        work=paths.work_dir() / "ingested",
        manifests=paths.data_dir() / "manifests",
        private_manifests=private / "manifests",
        dry_run=args.dry_run,
        replace=args.replace,
        slates=args.slates,
        gap_s=args.gap,
        trust_order=args.trust_order,
        turned=dict(args.turned),
    )
    print(report.render())
    return 0 if report.ok else 1


def _reference(args: argparse.Namespace) -> int:
    sheets = paths.private_dir() / "sheets"
    measurements = sheets / "watch-measurements.csv"
    with measurements.open(encoding="utf-8", newline="") as f:
        header = tuple(next(csv.reader(f), []))
    if header != MEASUREMENT_COLUMNS:
        print(f"{measurements.name}: the header must be {','.join(MEASUREMENT_COLUMNS)}")
        return 1
    watches, problems = build_reference(measurements, sheets / "watch-list.csv")
    for problem in problems:
        print(f"  problem {problem}")
    print(f"{len(watches)} watch(es) measured")
    for s in repeatability(watches):
        print(
            f"  {s.field}: {s.watches} watches, median range {s.median_range_mm} mm, "
            f"largest {s.largest_range_mm} mm ({s.worst_watch})"
        )
    if problems:
        print("Nothing was written.")
        return 1
    if not args.dry_run:
        target = paths.data_dir() / "catalogue" / "reference.csv"
        target.write_text(reference_csv(watches), encoding="utf-8", newline="\n")
        print(f"wrote {target}")
    return 0


def _phone_check(args: argparse.Namespace) -> int:
    checks, others = check_phone(Path(args.folder))
    width = max(len(c.name) for c in checks)
    for c in checks:
        print(f"{c.status:4}  {c.name:<{width}}  {c.detail}")
    if others:
        print(f"FAIL  other files: {', '.join(others)} (RAW or video?)")
    failed = others or any(c.status == "FAIL" for c in checks)
    return 1 if failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lugtolug", description="Lug to Lug's data tools")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("ingest", help="match a session's photos to the plan and copy them")
    run.add_argument("session", help="session ID, for example S03")
    run.add_argument("--dry-run", action="store_true", help="check only, write nothing")
    run.add_argument("--replace", action="store_true", help="overwrite a different earlier ingest")
    run.add_argument("--slates", type=int, default=1, help="slate photos at the start (1)")
    run.add_argument(
        "--gap", type=float, default=DEFAULT_GAP_S, help="seconds that separate placements (8)"
    )
    run.add_argument(
        "--trust-order",
        action="store_true",
        help="match in order when the count is right but the timing disagrees (check first)",
    )
    run.add_argument(
        "--turned",
        type=_turn,
        action="append",
        default=[],
        metavar="NAME=DEGREES",
        help="record that a checked photo was stored turned (repeatable)",
    )
    run.set_defaults(handler=_ingest)

    ref = commands.add_parser("reference", help="build data/catalogue/reference.csv")
    ref.add_argument("--dry-run", action="store_true", help="check only, write nothing")
    ref.set_defaults(handler=_reference)

    phone = commands.add_parser("phone-check", help="check test photos against the settings")
    phone.add_argument("folder", help="folder of test photos copied from the phone")
    phone.set_defaults(handler=_phone_check)

    args = parser.parse_args(argv)
    code: int = args.handler(args)
    return code
