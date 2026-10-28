"""The labelling tool's logic: label histories, saved annotations, and the proposer."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

from lugtolug_core.contracts.annotation import Flags
from lugtolug_ml.synthetic.generate import generate
from lugtolug_ml.synthetic.render import render
from lugtolug_ml.synthetic.scene import sample_scene
from lugtolug_tools.ingest import PUBLIC_COLUMNS
from lugtolug_tools.labelling.propose import PROPOSER, propose_case_outline
from lugtolug_tools.labelling.store import (
    Layer,
    Photo,
    benchmark_photos,
    build_annotation,
    demo_photos,
    label_path,
    layers_from,
    load,
    save,
)

WHEN = datetime(2026, 11, 3, 10, 12, tzinfo=UTC)
NO_FLAGS = Flags(
    blurred=False, glare=False, occluded=False, strap_moved=False, unusable=False, note=""
)
PHOTO = Photo("P01_S03_T20-DAY_07_W12_1", "S03", Path("x.jpg"), "a" * 64, "W12")
RING = [(100 + 40 * np.cos(t), 80 + 30 * np.sin(t)) for t in np.linspace(0, 6, 8)]


def _layers(**kw: Layer) -> dict[str, Layer]:
    layers = {name: Layer() for name in ("case_outline", "dial_outline", "radial", "ulnar")}
    layers.update(kw)
    return layers


def _origin(layer: Layer) -> str:
    return layer.origin  # read fresh: the methods below change it


def test_a_layer_remembers_how_it_was_made() -> None:
    drawn = Layer()
    drawn.add(1, 2)
    assert _origin(drawn) == "drawn"
    proposed = Layer()
    proposed.propose([(1, 2), (3, 4)], PROPOSER)
    assert _origin(proposed) == "proposed"
    proposed.move(0, 1.5, 2)
    assert _origin(proposed) == "corrected"
    other = Layer()
    other.propose([(1, 2), (3, 4)], PROPOSER)
    other.add(5, 6)
    assert _origin(other) == "corrected"
    other.undo()
    other.undo()
    other.undo()
    assert (_origin(other), other.points, other.proposer) == ("empty", [], None)


def test_provenance_says_who_checked_what() -> None:
    accepted = Layer()
    accepted.propose(RING, PROPOSER)
    corrected = Layer()
    corrected.propose(RING, PROPOSER)
    corrected.add(140, 80)
    edge = Layer()
    edge.add(0, 10)
    edge.add(200, 12)
    annotation = build_annotation(
        PHOTO,
        (4000, 3000),
        _layers(case_outline=accepted, dial_outline=corrected, radial=edge, ulnar=edge),
        watch_id="W12",
        labeller="P01",
        flags=NO_FLAGS,
        created=WHEN,
        sha256="a" * 64,
    )
    assert annotation.case_outline is not None
    assert annotation.case_outline.provenance.method == "model_proposed_person_accepted"
    assert annotation.case_outline.provenance.proposer == PROPOSER
    assert annotation.dial_outline is not None
    assert annotation.dial_outline.provenance.method == "model_proposed_person_corrected"
    assert annotation.wrist_edges is not None
    assert annotation.wrist_edges.provenance.method == "person_drawn"
    assert annotation.wrist_edges.provenance.proposer is None
    assert annotation.identity is not None
    assert annotation.identity.provenance.method == "session_sheet"
    assert annotation.identity.provenance.labeller is None


def test_a_changed_watch_is_the_labeller_s_call() -> None:
    annotation = build_annotation(
        PHOTO,
        (4000, 3000),
        _layers(),
        watch_id="W13",
        labeller="P01",
        flags=NO_FLAGS,
        created=WHEN,
        sha256="a" * 64,
    )
    assert annotation.identity is not None
    assert annotation.identity.provenance.method == "person_drawn"
    assert annotation.identity.provenance.labeller == "P01"
    assert annotation.case_outline is None


@pytest.mark.parametrize(
    ("layers", "message"),
    [
        (_layers(case_outline=Layer([(1, 1), (2, 2), (3, 1)], "drawn")), "at least five points"),
        (_layers(radial=Layer([(1, 1), (2, 2)], "drawn")), "each wrist edge needs"),
    ],
)
def test_half_made_labels_are_refused(layers: dict[str, Layer], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build_annotation(
            PHOTO,
            (4000, 3000),
            layers,
            watch_id="W12",
            labeller="P01",
            flags=NO_FLAGS,
            created=WHEN,
            sha256="a" * 64,
        )


def test_a_saved_annotation_reopens_with_its_history(tmp_path: Path) -> None:
    case = Layer()
    case.propose(RING, PROPOSER)
    case.move(2, 120, 100)
    annotation = build_annotation(
        PHOTO,
        (4000, 3000),
        _layers(case_outline=case),
        watch_id="W12",
        labeller="P01",
        flags=NO_FLAGS,
        created=WHEN,
        sha256="a" * 64,
    )
    path = label_path(tmp_path, PHOTO)
    save(annotation, path)
    assert path == tmp_path / "S03" / "P01_S03_T20-DAY_07_W12_1.json"
    assert load(path) == annotation
    reopened = layers_from(load(path))
    assert reopened["case_outline"].origin == "corrected"
    assert reopened["case_outline"].proposer == PROPOSER
    assert reopened["case_outline"].points == case.points
    assert load(tmp_path / "missing.json") is None


def test_benchmark_and_demo_photos_are_found(tmp_path: Path) -> None:
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    with (manifests / "S03.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PUBLIC_COLUMNS)
        writer.writeheader()
        row = dict.fromkeys(PUBLIC_COLUMNS, "")
        row.update(image_id=PHOTO.image_id, session_id="S03", watch_id="W12", sha256="b" * 64)
        writer.writerow(row)
    (photo,) = benchmark_photos(manifests, tmp_path / "ingested")
    assert photo.path == tmp_path / "ingested" / "S03" / f"{PHOTO.image_id}.jpg"
    assert (photo.watch_id, photo.sha256) == ("W12", "b" * 64)

    generate(tmp_path / "synthetic", 1, width=192)
    (demo,) = demo_photos(tmp_path / "synthetic")
    assert demo.path.exists()
    assert demo.truth is not None
    assert len(demo.truth["case_outline"]) == 180


def _densify(outline: list[list[float]], times: int = 10) -> npt.NDArray[np.float64]:
    ring = np.array([*outline, outline[0]])
    steps = np.linspace(0, 1, times, endpoint=False)[:, None]
    return np.concatenate([a + steps * (b - a) for a, b in pairwise(ring)])


def test_the_proposal_lands_on_the_case_edge() -> None:
    scene = sample_scene(np.random.default_rng([3, 11]), 960, seed=(3, 11), tilt_deg=0.0)
    rendered = render(scene)
    outlines = rendered.labels.outlines
    edges = [outlines.case_top] + ([outlines.bezel_top] if outlines.bezel_top else [])
    dense = np.concatenate([_densify(edge) for edge in edges])
    truth = np.array(outlines.case_top)
    centre = (float(truth[:, 0].mean()), float(truth[:, 1].mean()))
    grey = np.asarray(Image.fromarray(rendered.image).convert("L"), dtype=float)
    found = propose_case_outline(grey, centre, (float(truth[0, 0]), float(truth[0, 1])))
    assert len(found) >= 24
    # The proposal finds the outermost edge, the case's or the bezel's.
    distances = [float(np.min(np.hypot(*(dense - p).T))) for p in found]
    assert float(np.median(distances)) < 2.0, distances


def test_nothing_is_proposed_on_a_blank_image() -> None:
    assert propose_case_outline(np.full((200, 200), 128.0), (100, 100), (150, 100)) == []
    assert propose_case_outline(np.full((200, 200), 128.0), (100, 100), (101, 100)) == []


def test_the_page_opens_without_photos_and_with_the_demo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUGTOLUG_WORK_DIR", str(tmp_path))
    app = Path(__file__).resolve().parents[1] / "src" / "lugtolug_tools" / "labelling" / "app.py"
    page = AppTest.from_file(str(app), default_timeout=60).run()
    assert not page.exception
    generate(tmp_path / "synthetic" / "v0", 1, width=192)
    page.sidebar.radio[0].set_value("Demo (synthetic)").run()
    assert not page.exception
    assert page.sidebar.button  # the Save button is there
