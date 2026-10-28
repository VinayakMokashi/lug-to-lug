"""Generate synthetic data v0.

    uv run poe synth --count 1000                     # into ../work/synthetic/v0
    uv run poe synth --count 8 --width 512 --out DIR  # a small trial

Sample i is drawn from a generator seeded with [seed, i], so any sample can be
re-rendered on its own and a run can be extended (--start) without changing the samples
already made. Writes, for each sample, `images/<id>.jpg`, `masks/<id>.png` (one class per
pixel, see labels.CLASSES) and `labels/<id>.json`, plus `manifest.csv` with one row per
sample and `README.md` describing the run. Samples already on disk are skipped, so an
interrupted run is finished by running the same command again.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image

from lugtolug_ml import __version__
from lugtolug_ml.synthetic.labels import CLASSES, SyntheticLabels
from lugtolug_ml.synthetic.render import CASE, DIAL, render
from lugtolug_ml.synthetic.scene import sample_scene

MANIFEST_COLUMNS = (
    "sample_id",
    "seed",
    "skin_tone",
    "light",
    "surface",
    "tilt_deg",
    "distance_mm",
    "case_shape",
    "case_diameter_mm",
    "bezel_type",
    "strap_type",
    "px_per_mm",
    "case_pixels",
    "dial_pixels",
    "wrist_width_mm",
)


def default_out() -> Path:
    """The work folder next to the repository (LUGTOLUG_WORK_DIR overrides it)."""
    repo = Path(__file__).resolve().parents[4]
    work = os.environ.get("LUGTOLUG_WORK_DIR") or repo.parent / "work"
    return Path(work) / "synthetic" / "v0"


def render_sample(job: tuple[int, int, int, str]) -> str:
    """Render and write one sample, unless it is already there; returns its ID."""
    seed, index, width, out = job
    folder = Path(out)
    sample_id = f"{index:06d}"
    label_path = folder / "labels" / f"{sample_id}.json"
    if label_path.exists():
        return sample_id
    scene = sample_scene(np.random.default_rng([seed, index]), width, seed=(seed, index))
    rendered = render(scene, sample_id)
    image = Image.fromarray(rendered.image)
    image.save(folder / "images" / f"{sample_id}.jpg", quality=scene.post.jpeg_quality)
    Image.fromarray(rendered.classes).save(folder / "masks" / f"{sample_id}.png", optimize=True)
    # The labels last, and renamed into place whole, so a sample counts as made only once
    # all three files are complete.
    partial = label_path.with_suffix(".json.partial")
    partial.write_text(rendered.labels.model_dump_json(), encoding="utf-8", newline="\n")
    partial.replace(label_path)
    return sample_id


def manifest_row(labels: SyntheticLabels) -> dict[str, object]:
    counts = labels.pixel_counts
    return {
        "sample_id": labels.sample_id,
        "seed": ":".join(str(s) for s in labels.seed),
        "skin_tone": labels.conditions.skin_tone,
        "light": labels.conditions.light,
        "surface": labels.conditions.surface,
        "tilt_deg": round(labels.conditions.tilt_deg, 2),
        "distance_mm": round(labels.conditions.distance_mm, 1),
        "case_shape": labels.spec.case.shape,
        "case_diameter_mm": labels.spec.case.diameter_mm,
        "bezel_type": labels.spec.bezel.type,
        "strap_type": labels.spec.strap.type,
        "px_per_mm": round(labels.px_per_mm, 4),
        "case_pixels": counts.get(CASE, 0) + counts.get(DIAL, 0),
        "dial_pixels": counts.get(DIAL, 0),
        "wrist_width_mm": round(labels.wrist.width_mm, 2),
    }


def write_manifest(out: Path) -> int:
    """manifest.csv from every sample's labels; returns the number of samples."""
    rows = [
        manifest_row(SyntheticLabels.model_validate_json(path.read_text(encoding="utf-8")))
        for path in sorted((out / "labels").glob("*.json"))
    ]
    with (out / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def generate(
    out: Path, count: int, *, start: int = 0, seed: int = 0, width: int = 1024, workers: int = 1
) -> int:
    """Make samples start .. start + count - 1, skipping any already made.

    Safe to interrupt: running the same command again finishes the job. Returns the
    number of samples in the folder.
    """
    for sub in ("images", "masks", "labels"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    jobs = [(seed, index, width, str(out)) for index in range(start, start + count)]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            list(pool.map(render_sample, jobs, chunksize=4))
    else:
        for job in jobs:
            render_sample(job)
    return write_manifest(out)


def _readme(out: Path, args: argparse.Namespace, total: int, seconds: float) -> None:
    classes = "\n".join(f"- {value}: {name}" for value, name in CLASSES.items())
    command = (
        f"uv run poe synth --count {args.count} --start {args.start} "
        f"--seed {args.seed} --width {args.width}"
    )
    text = f"""# Synthetic data v0

Made by lugtolug-ml {__version__} on {datetime.now(UTC):%Y-%m-%d %H:%M} UTC. Training only,
never evaluation. Everything here can be rebuilt with the same command and seed.

- Last command: `{command}`
- Samples in this folder: {total}
- That run: {args.count} samples in {seconds / 60:.1f} minutes with {args.workers} worker(s)

Folders: `images/` (JPEG), `masks/` (PNG, one class per pixel), `labels/` (JSON, see
`lugtolug_ml.synthetic.labels`), and `manifest.csv`.

Mask classes:

{classes}
"""
    (out / "README.md").write_text(text, encoding="utf-8", newline="\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic data v0")
    parser.add_argument("--count", type=int, default=100, help="samples to make (100)")
    parser.add_argument("--start", type=int, default=0, help="index of the first sample (0)")
    parser.add_argument("--seed", type=int, default=0, help="the run's seed (0)")
    parser.add_argument("--width", type=int, default=1024, help="image width in pixels (1024)")
    parser.add_argument("--workers", type=int, default=min(8, max(1, (os.cpu_count() or 2) - 2)))
    parser.add_argument("--out", type=Path, default=None, help="folder (../work/synthetic/v0)")
    args = parser.parse_args(argv)
    out = args.out or default_out()
    began = time.perf_counter()
    total = generate(
        out, args.count, start=args.start, seed=args.seed, width=args.width, workers=args.workers
    )
    seconds = time.perf_counter() - began
    _readme(out, args, total, seconds)
    last = args.start + args.count - 1
    print(f"samples {args.start}-{last} in {seconds:.0f} s -> {out} ({total} in all)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
