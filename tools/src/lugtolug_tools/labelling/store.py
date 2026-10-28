"""Where the labelling tool finds photos and keeps labels, and how each label's history is
recorded.

Benchmark photos are the ingested copies (work folder, `ingested/<session>/`) listed in
the public manifests (`data/manifests/<session>.csv`). Labels go to
`data/labels/<session>/<image_id>.json` in the ImageAnnotation format, so they are
reviewed and versioned like code.

Demo mode opens the synthetic set instead, shows each image's true outlines for
comparison, and saves to the work folder, never to `data/labels`.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from lugtolug_core.contracts.annotation import (
    Flags,
    Identity,
    ImageAnnotation,
    Outline,
    Point,
    Provenance,
    WristEdges,
)
from lugtolug_ml.synthetic.labels import SyntheticLabels
from lugtolug_tools import __version__

TOOL = f"lugtolug-tools {__version__} labelling"
LAYERS = ("case_outline", "dial_outline", "radial", "ulnar")
Origin = Literal["empty", "drawn", "proposed", "corrected"]
Method = Literal[
    "person_drawn", "model_proposed_person_accepted", "model_proposed_person_corrected"
]
METHODS: dict[Origin, Method] = {
    "drawn": "person_drawn",
    "proposed": "model_proposed_person_accepted",
    "corrected": "model_proposed_person_corrected",
}


@dataclass
class Layer:
    """The points of one label being made, and how they came about."""

    points: list[tuple[float, float]] = field(default_factory=list)
    origin: Origin = "empty"
    proposer: str | None = None

    def add(self, x: float, y: float) -> None:
        self.points.append((round(x, 2), round(y, 2)))
        self.origin = "corrected" if self.origin in ("proposed", "corrected") else "drawn"

    def move(self, index: int, x: float, y: float) -> None:
        self.points[index] = (round(x, 2), round(y, 2))
        if self.origin == "proposed":
            self.origin = "corrected"

    def undo(self) -> None:
        if self.points:
            self.points.pop()
            if self.origin == "proposed":
                self.origin = "corrected"
        if not self.points:
            self.clear()

    def clear(self) -> None:
        self.points, self.origin, self.proposer = [], "empty", None

    def propose(self, points: list[tuple[float, float]], proposer: str) -> None:
        self.points = [(round(x, 2), round(y, 2)) for x, y in points]
        self.origin, self.proposer = "proposed", proposer

    def provenance(self, labeller: str, created: datetime) -> Provenance:
        if self.origin == "empty":
            raise ValueError("an empty layer has no provenance")
        return Provenance(
            method=METHODS[self.origin],
            labeller=labeller,
            proposer=None if self.origin == "drawn" else self.proposer,
            tool=TOOL,
            created=created,
        )


@dataclass(frozen=True)
class Photo:
    image_id: str
    session_id: str
    path: Path
    sha256: str  # from the manifest; checked against the file when it is opened
    watch_id: str
    truth: dict[str, list[list[float]]] | None = None  # demo only: the true outlines


def benchmark_photos(manifests: Path, ingested: Path) -> list[Photo]:
    """Every photo listed in the public manifests, in manifest order."""
    photos = []
    for manifest in sorted(manifests.glob("*.csv")):
        with manifest.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                photos.append(
                    Photo(
                        image_id=row["image_id"],
                        session_id=row["session_id"],
                        path=ingested / row["session_id"] / f"{row['image_id']}.jpg",
                        sha256=row["sha256"],
                        watch_id=row["watch_id"],
                    )
                )
    return photos


def demo_photos(synthetic: Path, limit: int = 200) -> list[Photo]:
    """Synthetic samples, with their true outlines to compare against."""
    photos = []
    for path in sorted((synthetic / "labels").glob("*.json"))[:limit]:
        labels = SyntheticLabels.model_validate_json(path.read_text(encoding="utf-8"))
        image = synthetic / "images" / f"{labels.sample_id}.jpg"
        truth = {
            "case_outline": labels.outlines.case_top,
            "dial_outline": labels.outlines.opening_top,
        }
        if labels.outlines.bezel_top:
            truth["bezel_outline"] = labels.outlines.bezel_top
        photos.append(
            Photo(
                image_id=f"synthetic_{labels.sample_id}",
                session_id="demo",
                path=image,
                sha256="",
                watch_id="W00",
                truth=truth,
            )
        )
    return photos


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label_path(labels: Path, photo: Photo) -> Path:
    return labels / photo.session_id / f"{photo.image_id}.json"


def _points(layer: Layer) -> list[Point]:
    return [Point(x=x, y=y) for x, y in layer.points]


def build_annotation(
    photo: Photo,
    size: tuple[int, int],
    layers: dict[str, Layer],
    *,
    watch_id: str,
    labeller: str,
    flags: Flags,
    created: datetime,
    sha256: str,
) -> ImageAnnotation:
    """The annotation to save. Raises ValueError for a label that is started but too short."""
    outlines: dict[str, Outline | None] = {}
    for name in ("case_outline", "dial_outline"):
        layer = layers[name]
        if layer.origin == "empty":
            outlines[name] = None
        elif len(layer.points) < 5:
            raise ValueError(f"{name.replace('_', ' ')} needs at least five points")
        else:
            outlines[name] = Outline(
                points=_points(layer), provenance=layer.provenance(labeller, created)
            )
    radial, ulnar = layers["radial"], layers["ulnar"]
    edges = None
    if radial.origin != "empty" or ulnar.origin != "empty":
        if len(radial.points) < 2 or len(ulnar.points) < 2:
            raise ValueError("each wrist edge needs at least two points")
        # One provenance for the pair: the less checked of the two.
        order = ["proposed", "corrected", "drawn"]
        weaker = radial if order.index(radial.origin) <= order.index(ulnar.origin) else ulnar
        edges = WristEdges(
            radial=_points(radial),
            ulnar=_points(ulnar),
            provenance=weaker.provenance(labeller, created),
        )
    from_sheet = watch_id == photo.watch_id
    identity = Identity(
        watch_id=watch_id,
        provenance=Provenance(
            method="session_sheet" if from_sheet else "person_drawn",
            labeller=None if from_sheet else labeller,
            proposer=None,
            tool=TOOL,
            created=created,
        ),
    )
    return ImageAnnotation(
        annotation_version=1,
        image_id=photo.image_id,
        image_sha256=sha256,
        width=size[0],
        height=size[1],
        case_outline=outlines["case_outline"],
        dial_outline=outlines["dial_outline"],
        wrist_edges=edges,
        identity=identity,
        flags=flags,
    )


def save(annotation: ImageAnnotation, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = annotation.model_dump_json(indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def load(path: Path) -> ImageAnnotation | None:
    if not path.exists():
        return None
    return ImageAnnotation.model_validate_json(path.read_text(encoding="utf-8"))


_ORIGINS: dict[str, Origin] = {
    "person_drawn": "drawn",
    "model_proposed_person_accepted": "proposed",
    "model_proposed_person_corrected": "corrected",
}


def layers_from(annotation: ImageAnnotation | None) -> dict[str, Layer]:
    """Editable layers from a saved annotation, keeping each label's history."""
    layers = {name: Layer() for name in LAYERS}
    if annotation is None:
        return layers
    for name in ("case_outline", "dial_outline"):
        outline: Outline | None = getattr(annotation, name)
        if outline is not None:
            layers[name] = Layer(
                points=[(p.x, p.y) for p in outline.points],
                origin=_ORIGINS.get(outline.provenance.method, "drawn"),
                proposer=outline.provenance.proposer,
            )
    edges = annotation.wrist_edges
    if edges is not None:
        origin = _ORIGINS.get(edges.provenance.method, "drawn")
        for name, points in (("radial", edges.radial), ("ulnar", edges.ulnar)):
            layers[name] = Layer([(p.x, p.y) for p in points], origin, edges.provenance.proposer)
    return layers
