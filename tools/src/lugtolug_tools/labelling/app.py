"""The labelling tool: `uv run poe label` opens it in the browser.

Click the overview to choose where to zoom; click the zoomed view to add points to the
chosen label. For a case outline, "Propose" takes two clicks in the zoomed view (the
middle of the case, then a point on its edge) and suggests the rest, to accept or
correct. Every label is saved with its history: drawn, accepted or corrected, by whom,
and with which tool.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates

from lugtolug_core.contracts.annotation import Flags
from lugtolug_core.geometry import fit_ellipse
from lugtolug_tools import paths
from lugtolug_tools.labelling.propose import PROPOSER, propose_case_outline
from lugtolug_tools.labelling.store import (
    LAYERS,
    Layer,
    Photo,
    benchmark_photos,
    build_annotation,
    demo_photos,
    file_sha256,
    label_path,
    layers_from,
    load,
    save,
)

NAMES = {
    "case_outline": "Case outline",
    "dial_outline": "Dial opening",
    "radial": "Wrist edge, thumb side",
    "ulnar": "Wrist edge, little-finger side",
}
COLOURS = {
    "case_outline": (255, 0, 255),
    "dial_outline": (0, 210, 255),
    "radial": (255, 210, 0),
    "ulnar": (255, 120, 0),
}
OVERVIEW_WIDTH = 900
ZOOM_PIXELS = 640  # the zoomed view's size on screen
state: Any = st.session_state


@st.cache_resource(max_entries=3)
def open_image(path: str) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGB")


def draw(
    canvas: Image.Image,
    layers: dict[str, Layer],
    to_screen: Any,
    truth: dict[str, list[list[float]]] | None,
) -> Image.Image:
    shown = canvas.copy()
    pen = ImageDraw.Draw(shown)
    for outline in (truth or {}).values():
        pen.line([to_screen(x, y) for x, y in [*outline, outline[0]]], fill=(60, 220, 90), width=1)
    for name, layer in layers.items():
        colour = COLOURS[name]
        points = [to_screen(x, y) for x, y in layer.points]
        if name in ("radial", "ulnar") and len(points) > 1:
            pen.line(points, fill=colour, width=2)
        if name in ("case_outline", "dial_outline") and len(layer.points) >= 5:
            try:
                ellipse = fit_ellipse(np.array(layer.points))
                ring = [to_screen(x, y) for x, y in ellipse.points(120)]
                pen.line([*ring, ring[0]], fill=colour, width=1)
            except ValueError:
                pass
        for px, py in points:
            pen.ellipse([px - 3, py - 3, px + 3, py + 3], outline=colour, width=2)
    return shown


def _propose(
    image: Image.Image, centre: tuple[float, float], edge: tuple[float, float]
) -> list[tuple[float, float]]:
    """Run the proposer on a crop around the case, then shift its points back."""
    reach = 1.4 * float(np.hypot(edge[0] - centre[0], edge[1] - centre[1])) + 8
    left, top = max(0, round(centre[0] - reach)), max(0, round(centre[1] - reach))
    box = (
        left,
        top,
        min(image.width, round(centre[0] + reach)),
        min(image.height, round(centre[1] + reach)),
    )
    grey = np.asarray(image.crop(box).convert("L"), dtype=float)
    shift = (centre[0] - left, centre[1] - top)
    found = propose_case_outline(grey, shift, (edge[0] - left, edge[1] - top))
    return [(x + left, y + top) for x, y in found]


def clicked(key: str, value: dict[str, Any] | None) -> tuple[float, float] | None:
    """A new click on a view, in that view's displayed pixels; None for an old one."""
    if not value or state.get(f"last_{key}") == value.get("unix_time"):
        return None
    state[f"last_{key}"] = value.get("unix_time")
    return float(value["x"]) + 0.5, float(value["y"]) + 0.5


def photos_for(source: str) -> tuple[list[Photo], Any]:
    if source == "Benchmark":
        found = benchmark_photos(paths.data_dir() / "manifests", paths.work_dir() / "ingested")
        return [p for p in found if p.path.exists()], paths.data_dir() / "labels"
    synthetic = paths.work_dir() / "synthetic" / "v0"
    return demo_photos(synthetic), paths.work_dir() / "labelling-demo"


def main() -> None:
    st.set_page_config(page_title="Lug to Lug labelling", layout="wide")
    source = st.sidebar.radio("Photos", ["Benchmark", "Demo (synthetic)"])
    photos, labels_dir = photos_for(source)
    if not photos:
        st.info(
            "No photos to label yet. Benchmark photos appear once a session is ingested "
            "(`uv run poe ingest S01`); the demo needs synthetic data (`uv run poe synth`)."
        )
        return
    labeller = st.sidebar.text_input("Labeller (participant ID)", value="P01")
    index = st.sidebar.selectbox(
        "Photo",
        range(len(photos)),
        format_func=lambda i: (
            ("done  " if label_path(labels_dir, photos[i]).exists() else "      ")
            + photos[i].image_id
        ),
    )
    photo = photos[index]
    image = open_image(str(photo.path))
    if state.get("loaded_for") != photo.image_id:
        saved = load(label_path(labels_dir, photo))
        state.layers = layers_from(saved)
        state.watch_id = saved.identity.watch_id if saved and saved.identity else photo.watch_id
        state.flags = (
            saved.flags
            if saved
            else Flags(
                blurred=False,
                glare=False,
                occluded=False,
                strap_moved=False,
                unusable=False,
                note="",
            )
        )
        state.centre = (image.width / 2, image.height / 2)
        state.proposing = []
        state.loaded_for = photo.image_id
    layers: dict[str, Layer] = state.layers

    name = st.sidebar.radio("Label", LAYERS, format_func=lambda n: NAMES[n])
    zoom = st.sidebar.select_slider("Zoom", options=[1, 2, 3, 4, 6], value=2)
    layer = layers[name]
    buttons = st.sidebar.columns(3)
    if buttons[0].button("Undo"):
        layer.undo()
    if buttons[1].button("Clear"):
        layer.clear()
    if buttons[2].button("Propose", disabled=name != "case_outline"):
        state.proposing = ["waiting"]
    # Keys carry the photo, so each photo's answers stay its own.
    k = photo.image_id
    watch_id = st.sidebar.text_input("Watch", value=state.watch_id, key=f"watch-{k}")
    f = state.flags
    flags = Flags(
        blurred=st.sidebar.checkbox("Blurred", value=f.blurred, key=f"blurred-{k}"),
        glare=st.sidebar.checkbox("Glare", value=f.glare, key=f"glare-{k}"),
        occluded=st.sidebar.checkbox("Something covers it", value=f.occluded, key=f"occ-{k}"),
        strap_moved=st.sidebar.checkbox(
            "Watch out of place", value=f.strap_moved, key=f"moved-{k}"
        ),
        unusable=st.sidebar.checkbox("Unusable", value=f.unusable, key=f"unusable-{k}"),
        note=st.sidebar.text_input("Note", value=f.note, key=f"note-{k}"),
    )

    scale = OVERVIEW_WIDTH / image.width
    left, right = st.columns([3, 2])
    with left:
        st.caption(f"{photo.image_id}: click to choose where to zoom")
        small = image.resize((OVERVIEW_WIDTH, round(image.height * scale)))
        shown = draw(small, layers, lambda x, y: (x * scale, y * scale), photo.truth)
        hit = clicked("overview", streamlit_image_coordinates(shown, key=f"o-{photo.image_id}"))
        if hit:
            state.centre = (hit[0] / scale, hit[1] / scale)
    half = ZOOM_PIXELS / zoom / 2
    cx, cy = state.centre
    x0, y0 = cx - half, cy - half
    crop = image.crop((round(x0), round(y0), round(x0 + 2 * half), round(y0 + 2 * half)))
    x0, y0 = round(x0), round(y0)
    view = crop.resize((ZOOM_PIXELS, ZOOM_PIXELS), Image.Resampling.LANCZOS)

    def to_view(x: float, y: float) -> tuple[float, float]:
        return (x - x0) * zoom, (y - y0) * zoom

    with right:
        waiting = bool(state.proposing)
        hint = (
            "Propose: click the middle of the case, then a point on its edge"
            if waiting
            else f"{NAMES[name]}: click to add a point"
        )
        st.caption(hint)
        shown = draw(view, layers, to_view, photo.truth)
        hit = clicked("zoom", streamlit_image_coordinates(shown, key=f"z-{photo.image_id}"))
        if hit:
            point = (x0 + hit[0] / zoom, y0 + hit[1] / zoom)
            if waiting:
                state.proposing = [p for p in state.proposing if p != "waiting"] + [point]
                if len(state.proposing) == 2:
                    found = _propose(image, state.proposing[0], state.proposing[1])
                    state.proposing = []
                    if found:
                        layers["case_outline"].propose(found, PROPOSER)
                    else:
                        st.warning("No clear outline found there: draw it by clicking.")
                st.rerun()
            else:
                layer.add(*point)
                st.rerun()
        st.caption(
            "  ·  ".join(
                f"{NAMES[n]}: {len(v.points)} points ({v.origin})" for n, v in layers.items()
            )
        )

    if st.sidebar.button("Save", type="primary"):
        sha = file_sha256(photo.path)
        if photo.sha256 and sha != photo.sha256:
            st.error("This photo's file changed since it was ingested; re-ingest the session.")
            return
        try:
            annotation = build_annotation(
                photo,
                image.size,
                layers,
                watch_id=watch_id,
                labeller=labeller,
                flags=flags,
                created=datetime.now().astimezone(),
                sha256=sha,
            )
        except ValueError as error:
            st.error(str(error))
            return
        save(annotation, label_path(labels_dir, photo))
        st.success(f"Saved {photo.image_id}")


main()
