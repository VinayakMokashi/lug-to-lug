"""Synthetic data v0: the labels agree with the image, and runs are reproducible."""

from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest
from PIL import Image, ImageDraw

from lugtolug_core.geometry import fit_ellipse
from lugtolug_core.standin import check_spec
from lugtolug_ml.synthetic.generate import generate
from lugtolug_ml.synthetic.labels import SyntheticLabels
from lugtolug_ml.synthetic.render import CASE, DIAL, SKIN, Rendered, render
from lugtolug_ml.synthetic.scene import sample_scene, sample_spec

WIDTH = 480


def _render(index: int, tilt: float | None = None) -> Rendered:
    scene = sample_scene(np.random.default_rng([3, index]), WIDTH, seed=(3, index), tilt_deg=tilt)
    return render(scene, f"{index:06d}")


def _polygon_mask(points: list[list[float]], size: tuple[int, int]) -> npt.NDArray[np.bool_]:
    canvas = Image.new("1", size, 0)
    ImageDraw.Draw(canvas).polygon([tuple(p) for p in points], fill=1)
    return np.asarray(canvas, dtype=bool)


@pytest.fixture(scope="module")
def straight_down() -> Rendered:
    return _render(11, tilt=0.0)


@pytest.fixture(scope="module")
def tilted() -> Rendered:
    return _render(12, tilt=30.0)


def test_every_class_appears(straight_down: Rendered) -> None:
    counts = straight_down.labels.pixel_counts
    assert set(counts) >= {0, SKIN, CASE, DIAL}
    assert straight_down.image.shape == (360, 480, 3)
    assert straight_down.classes.shape == (360, 480)


def test_the_case_outline_is_the_case_in_the_mask(straight_down: Rendered) -> None:
    labels = straight_down.labels
    size = (labels.camera.width, labels.camera.height)
    head = np.isin(straight_down.classes, (CASE, DIAL))
    outlines = [labels.outlines.case_top] + (
        [labels.outlines.bezel_top] if labels.outlines.bezel_top else []
    )
    drawn = np.zeros_like(head)
    for outline in outlines:
        drawn |= _polygon_mask(outline, size)
    iou = (head & drawn).sum() / (head | drawn).sum()
    assert iou > 0.8, iou
    dial = straight_down.classes == DIAL
    inside = _polygon_mask(labels.outlines.opening_top, size)
    assert (dial & inside).sum() / dial.sum() > 0.97


def test_straight_down_a_round_case_is_a_circle_of_the_labelled_scale(
    straight_down: Rendered,
) -> None:
    labels = straight_down.labels
    if labels.spec.case.shape != "round":
        pytest.skip("this seed drew a non-round case")
    ellipse = labels.case_top_ellipse
    assert ellipse is not None
    assert labels.reference_circle is not None
    assert ellipse.b / ellipse.a > 0.98
    expected = labels.px_per_mm * labels.reference_circle.radius_mm
    assert ellipse.a == pytest.approx(expected, rel=0.03)


def test_tilting_squeezes_the_circle_by_the_cosine(tilted: Rendered) -> None:
    labels = tilted.labels
    if labels.spec.case.shape != "round":
        pytest.skip("this seed drew a non-round case")
    ellipse = fit_ellipse(np.array(labels.outlines.case_top))
    ratio = ellipse.b / ellipse.a
    roll = math.radians(abs(labels.conditions.roll_deg))
    assert (
        math.cos(math.radians(30) + roll) - 0.03 < ratio < math.cos(math.radians(30) - roll) + 0.03
    )


def test_the_wrist_is_found_on_both_sides(straight_down: Rendered) -> None:
    edges = straight_down.labels.wrist.edges
    assert edges is not None
    first, second = np.array(edges)
    assert np.linalg.norm(first - second) > 20


def test_the_same_seed_gives_the_same_sample() -> None:
    first, second = _render(5), _render(5)
    assert np.array_equal(first.image, second.image)
    assert np.array_equal(first.classes, second.classes)
    assert first.labels == second.labels


def test_labels_survive_a_round_trip(tilted: Rendered) -> None:
    text = tilted.labels.model_dump_json()
    assert SyntheticLabels.model_validate_json(text) == tilted.labels


def test_scenes_cover_every_skin_tone_and_valid_watches() -> None:
    tones: Counter[int] = Counter()
    for index in range(300):
        rng = np.random.default_rng([1, index])
        tones[sample_scene(rng, WIDTH).skin_tone] += 1
    assert set(tones) == set(range(1, 11))
    assert min(tones.values()) > 15
    for index in range(50):
        spec = sample_spec(np.random.default_rng([2, index]))
        assert check_spec(spec) == []
        assert "lugs.lug_to_lug_mm" not in spec.assumed  # every dimension is drawn


def test_generate_writes_a_reproducible_run(tmp_path: Path) -> None:
    assert generate(tmp_path / "a", 2, seed=4, width=192) == 2
    generate(tmp_path / "b", 2, seed=4, width=192)
    for sub, suffix in (("images", "jpg"), ("masks", "png"), ("labels", "json")):
        for sample in ("000000", "000001"):
            a = (tmp_path / "a" / sub / f"{sample}.{suffix}").read_bytes()
            b = (tmp_path / "b" / sub / f"{sample}.{suffix}").read_bytes()
            assert a == b
    with Image.open(tmp_path / "a" / "masks" / "000000.png") as mask:
        assert set(np.unique(np.asarray(mask))) <= {0, 1, 2, 3, 4, 5}


def test_an_interrupted_run_is_finished_by_running_it_again(tmp_path: Path) -> None:
    out = tmp_path / "run"
    generate(out, 2, seed=4, width=192)
    made = (out / "images" / "000000.jpg").stat().st_mtime_ns
    (out / "labels" / "000001.json").unlink()  # as if stopped while writing sample 1
    assert generate(out, 3, seed=4, width=192) == 3
    assert (out / "images" / "000000.jpg").stat().st_mtime_ns == made  # not redone
    with (out / "manifest.csv").open(encoding="utf-8") as f:
        manifest = list(csv.DictReader(f))
    assert [row["sample_id"] for row in manifest] == ["000000", "000001", "000002"]
    assert manifest[0]["seed"] == "4:0"
