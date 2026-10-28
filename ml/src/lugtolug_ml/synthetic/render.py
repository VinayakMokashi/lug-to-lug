"""Render a synthetic scene: an image, a class mask, and exact labels.

A ray caster on the CPU, in numpy. Each pixel's ray is intersected with:

- the surface the arm lies on, the plane z = 0;
- the forearm and the strap, implicit surfaces found by stepping down the ray and then
  bisecting;
- the watch, prisms in its own frame, sliced every 0.35 mm so their side walls appear
  when the camera is tilted.

The nearest hit is shaded with a key light, a fill light and a simple sky for metals to
reflect, with shadows traced towards the key light. Then comes what a phone camera adds:
exposure, vignetting, blur, noise and (when saved) JPEG compression.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from PIL import Image, ImageFilter

from lugtolug_core.geometry import FloatArray, fit_ellipse
from lugtolug_ml import __version__
from lugtolug_ml.synthetic.labels import (
    CameraLabel,
    Conditions,
    Heights,
    ImageEllipse,
    Outlines,
    ReferenceCircle,
    SyntheticLabels,
    WatchPose,
    WristLabel,
)
from lugtolug_ml.synthetic.palette import (
    LIGHTS,
    MATERIALS,
    MONK_SKIN_TONES,
    Material,
    hex_to_linear,
    linear_to_srgb,
)
from lugtolug_ml.synthetic.scene import BoolArray, Outline, Scene, WatchGeometry

IntArray = npt.NDArray[np.int64]

SKIN, STRAP, PARTS, CASE, DIAL = 1, 2, 3, 4, 5
STRAP_THICKNESS_MM = {"bracelet": 3.5, "leather": 2.5, "rubber": 3.0, "fabric": 1.5, "other": 2.5}
WATCH_SLICE_MM = 0.35
# Steps along each ray before bisecting. At 1 mm a 1024-px render differs from a 0.25 mm
# reference in about 60 pixels, all on the strap's edges (measured 2026-10-28).
ARM_STEP_MM = 1.0


@dataclass
class Rendered:
    image: npt.NDArray[np.uint8]  # height x width x 3, sRGB, before JPEG compression
    classes: npt.NDArray[np.uint8]  # height x width
    labels: SyntheticLabels


@dataclass
class Hits:
    """What each ray hit first."""

    t: FloatArray
    kind: IntArray  # one of the classes, 0 for the surface
    normal: FloatArray  # world normals, unit
    part: IntArray  # the watch solid's index, -1 elsewhere
    uv: FloatArray  # the hit in the watch's plane (for patterns on the watch and strap)
    cap: BoolArray  # the watch solid's top rather than its side
    inner: BoolArray  # the inside wall of a hole (the dial opening)


def _noise(rng: np.random.Generator, height: int, width: int, cells: int) -> FloatArray:
    """Smooth random variation around 0, with about `cells` blobs across the image."""
    grid = rng.normal(0, 1, (max(2, cells * height // width), cells)).astype(np.float32)
    image = Image.fromarray(grid, mode="F").resize((width, height), Image.Resampling.BICUBIC)
    values: FloatArray = np.asarray(image, dtype=float)
    return values


# ---------------------------------------------------------------------------------------
# Intersections


def _strap_field(scene: Scene, geometry: WatchGeometry, points: FloatArray) -> FloatArray:
    """Negative inside the strap: a band around the wrist, leaving from the lug tips.

    Under the watch there is no strap. Near the lug tips it is lifted to where the
    lugs hold it, then it ramps down onto the wrist over about 10 mm.
    """
    local = scene.to_watch(points)
    thickness = STRAP_THICKNESS_MM[scene.spec.strap.type]
    half_span = scene.spec.lugs.lug_to_lug_mm / 2
    across = np.abs(local[:, 1])
    in_band = np.abs(local[:, 0]) <= scene.spec.lugs.lug_width_mm / 2
    under_head = (across < half_span - 1.0) & (local[:, 2] > -8)
    lift = 0.3 * scene.spec.case.thickness_mm * np.clip(1 - (across - half_span + 1) / 10, 0, 1)
    field = scene.arm.field(points[:, 0], points[:, 1], points[:, 2], grow=thickness + lift)
    values: FloatArray = np.where(in_band & ~under_head, field, 1.0)
    return values


def _bounds(scene: Scene) -> tuple[float, float]:
    """A cylinder along x that holds the forearm, hand and strap: its axis height, radius."""
    arm = scene.arm
    a_max = max(arm.width_mm / 2 * 1.3, arm.hand_breadth_mm / 2)
    lift = 0.3 * scene.spec.case.thickness_mm
    radius = max(a_max, arm.thickness_mm / 2 * 1.1) + max(STRAP_THICKNESS_MM.values()) + lift + 2
    return arm.thickness_mm / 2, radius


def _chord(
    origins: FloatArray, directions: FloatArray, axis_z: float, radius: float
) -> tuple[FloatArray, FloatArray]:
    """Where lines enter and leave the bounding cylinder (nan where they miss it)."""
    dy, dz = directions[:, 1], directions[:, 2]
    oy, oz = origins[:, 1], origins[:, 2] - axis_z
    a = dy * dy + dz * dz
    b = 2 * (dy * oy + dz * oz)
    c = oy * oy + oz * oz - radius * radius
    disc = b * b - 4 * a * c
    root = np.sqrt(np.where(disc > 0, disc, np.nan))
    enter: FloatArray = (-b - root) / (2 * a)
    leave: FloatArray = (-b + root) / (2 * a)
    return enter, leave


def _arm_or_strap(
    scene: Scene, geometry: WatchGeometry, points: FloatArray, strap_reach: float
) -> tuple[FloatArray, FloatArray]:
    """The skin's field and the strap's field (1 where the strap can't be)."""
    skin = scene.arm.field(points[:, 0], points[:, 1], points[:, 2])
    strap = np.ones(len(points))
    near = np.abs(points[:, 0] - scene.watch_origin[0]) < strap_reach
    if near.any():
        strap[near] = _strap_field(scene, geometry, points[near])
    return skin, strap


def _cast_arm(
    scene: Scene, geometry: WatchGeometry, origin: FloatArray, rays: FloatArray
) -> tuple[FloatArray, IntArray, FloatArray]:
    """Where rays first meet the forearm, hand or strap: distance, kind and normal."""
    n = len(rays)
    t_hit = np.full(n, np.inf)
    kind = np.zeros(n, dtype=np.int64)
    normal = np.zeros((n, 3))
    axis_z, radius = _bounds(scene)
    enter, leave = _chord(np.tile(origin, (n, 1)), rays, axis_z, radius)
    index = np.flatnonzero(np.isfinite(enter) & (leave > 0))
    if len(index) == 0:
        return t_hit, kind, normal
    d = rays[index]
    t_now = np.maximum(enter[index], 0.0)
    t_end = leave[index]
    lugs = scene.spec.lugs
    strap_reach = lugs.lug_width_mm / 2 + 0.15 * lugs.lug_to_lug_mm + 3

    previous = t_now.copy()
    found = np.zeros(len(index), dtype=bool)
    open_rays = np.arange(len(index))
    while len(open_rays):
        points = origin + t_now[open_rays, None] * d[open_rays]
        skin, strap = _arm_or_strap(scene, geometry, points, strap_reach)
        hit = (skin <= 0) | (strap <= 0)
        found[open_rays[hit]] = True
        moving = open_rays[~hit]
        previous[moving] = t_now[moving]
        t_now[moving] += ARM_STEP_MM
        open_rays = moving[t_now[moving] <= t_end[moving]]
    if not found.any():
        return t_hit, kind, normal

    lo, hi = previous[found], t_now[found]  # outside, inside
    d_found = d[found]
    for _ in range(12):
        mid = (lo + hi) / 2
        skin, strap = _arm_or_strap(scene, geometry, origin + mid[:, None] * d_found, strap_reach)
        is_in = (skin <= 0) | (strap <= 0)
        hi = np.where(is_in, mid, hi)
        lo = np.where(is_in, lo, mid)
    points = origin + hi[:, None] * d_found
    _, strap_field = _arm_or_strap(scene, geometry, points, strap_reach)
    on_strap = strap_field <= 0

    # Normals from the field's gradient, by central differences.
    gradient = np.zeros_like(points)
    for axis in range(3):
        step = np.zeros(3)
        step[axis] = 0.05
        values = []
        for shifted in (points + step, points - step):
            skin, strap = _arm_or_strap(scene, geometry, shifted, strap_reach)
            values.append(np.where(on_strap, strap, skin))
        gradient[:, axis] = values[0] - values[1]
    gradient /= np.linalg.norm(gradient, axis=1, keepdims=True) + 1e-12

    rows = index[found]
    t_hit[rows] = hi
    kind[rows] = np.where(on_strap, STRAP, SKIN)
    normal[rows] = gradient
    return t_hit, kind, normal


def _cast_watch(
    scene: Scene, geometry: WatchGeometry, origin: FloatArray, rays: FloatArray, index: IntArray
) -> Hits:
    """The watch's solids, for the rays in `index`."""
    m = len(index)
    hits = Hits(
        t=np.full(m, np.inf),
        kind=np.zeros(m, dtype=np.int64),
        normal=np.zeros((m, 3)),
        part=np.full(m, -1, dtype=np.int64),
        uv=np.zeros((m, 2)),
        cap=np.zeros(m, dtype=bool),
        inner=np.zeros(m, dtype=bool),
    )
    if m == 0:
        return hits
    o = scene.to_watch(origin[None, :])[0]
    d = rays[index] @ scene.watch_axes
    for part, solid in enumerate(geometry.solids):
        steps = max(4, math.ceil((solid.top - solid.bottom) / WATCH_SLICE_MM) + 1)
        heights = np.linspace(solid.top, solid.bottom, steps)
        t_part = np.full(m, np.inf)
        uv = np.zeros((m, 2))
        cap = np.zeros(m, dtype=bool)
        inner = np.zeros(m, dtype=bool)
        was_in_hole = np.zeros(m, dtype=bool)
        for k, w in enumerate(heights):
            t = (w - o[2]) / d[:, 2]
            u, v = o[0] + t * d[:, 0], o[1] + t * d[:, 1]
            in_outer = solid.outer.inside(u, v)
            in_hole = solid.hole.inside(u, v) if solid.hole is not None else np.zeros(m, bool)
            new = in_outer & ~in_hole & ~np.isfinite(t_part) & (t > 0)
            t_part[new] = t[new]
            uv[new] = np.column_stack([u[new], v[new]])
            cap[new] = k == 0
            inner[new] = was_in_hole[new]
            was_in_hole = in_outer & in_hole
        closer = t_part < hits.t
        if not closer.any():
            continue
        local = np.zeros((int(closer.sum()), 3))
        at = uv[closer]
        on_cap = cap[closer]
        on_inner = inner[closer] & ~on_cap
        local[on_cap, 2] = 1.0
        walls = ~on_cap
        if walls.any():
            outer_normal = solid.outer.normal(at[walls, 0], at[walls, 1])
            if solid.hole is not None:
                hole_normal = -solid.hole.normal(at[walls, 0], at[walls, 1])
                outer_normal = np.where(on_inner[walls][:, None], hole_normal, outer_normal)
            local[walls, :2] = outer_normal
        hits.t[closer] = t_part[closer]
        hits.part[closer] = part
        hits.uv[closer] = at
        hits.cap[closer] = on_cap
        hits.inner[closer] = on_inner
        hits.normal[closer] = local @ scene.watch_axes.T
        if solid.kind in ("lug", "crown"):
            hits.kind[closer] = PARTS
        elif solid.kind == "case_low":
            in_opening = geometry.opening.inside(at[:, 0], at[:, 1])
            hits.kind[closer] = np.where(on_cap & in_opening, DIAL, CASE)
        else:
            hits.kind[closer] = CASE
    return hits


# ---------------------------------------------------------------------------------------
# Surfaces' colours (linear RGB)


def _dial_marks(scene: Scene, geometry: WatchGeometry, uv: FloatArray) -> FloatArray:
    """The dial's colour at points on it: plain hour markers and three hands."""
    dial = scene.spec.dial
    colour = np.tile(hex_to_linear(dial.colour), (len(uv), 1))
    un = uv[:, 0] / geometry.opening.a
    vn = uv[:, 1] / geometry.opening.b
    r = np.hypot(un, vn)
    theta = np.arctan2(un, vn)  # from 12 o'clock, clockwise as seen from above
    marker = np.zeros(len(uv), dtype=bool)
    step = math.pi / 6
    nearest = np.round(theta / step) * step
    gap = np.abs(theta - nearest) * r
    if dial.index_style in ("baton", "arabic", "roman"):
        width = np.where(np.isclose(np.mod(nearest, 2 * math.pi), 0), 0.05, 0.025)
        marker = (r > 0.78) & (r < 0.92) & (gap < width)
    elif dial.index_style == "dots":
        dot_u, dot_v = 0.86 * np.sin(nearest), 0.86 * np.cos(nearest)
        marker = np.hypot(un - dot_u, vn - dot_v) < 0.04
    colour[marker] = hex_to_linear(dial.index_colour)

    hours, minutes, seconds = scene.dial_time
    hands = (
        ((hours % 12 + minutes / 60) * math.pi / 6, 0.5, 0.045, dial.hands_colour),
        ((minutes + seconds / 60) * math.pi / 30, 0.78, 0.03, dial.hands_colour),
        (seconds * math.pi / 30, 0.88, 0.008, "#b3241f"),
    )
    for angle, length, hand_width, hand_colour in hands:
        along = un * math.sin(angle) + vn * math.cos(angle)
        across = un * math.cos(angle) - vn * math.sin(angle)
        half = hand_width * (1 - 0.5 * np.clip(along / length, 0, 1))
        on_hand = (along > -0.12 * length) & (along < length) & (np.abs(across) < half)
        colour[on_hand] = hex_to_linear(hand_colour)
    colour[r < 0.035] = hex_to_linear(dial.hands_colour)
    return colour


def _bezel_marks(
    scene: Scene, geometry: WatchGeometry, uv: FloatArray, base: FloatArray
) -> FloatArray:
    """A rotating bezel's minute scale, or a fluted bezel's ridges."""
    bezel = scene.spec.bezel
    if geometry.bezel is None:
        return base
    colour = base.copy()
    rb = np.hypot(uv[:, 0] / geometry.bezel.a, uv[:, 1] / geometry.bezel.b)
    theta = np.arctan2(uv[:, 0], uv[:, 1])
    if bezel.type == "rotating_insert" and bezel.markings != "none":
        minute = np.abs(theta - np.round(theta / (math.pi / 30)) * (math.pi / 30))
        five = np.abs(theta - np.round(theta / (math.pi / 6)) * (math.pi / 6))
        tick = ((minute < 0.012) & (rb > 0.9)) | ((five < 0.03) & (rb > 0.84))
        tick |= (np.abs(theta) < 0.07 * (rb - 0.78) / 0.2) & (rb > 0.8)  # the triangle at 12
        colour[tick] = hex_to_linear(scene.spec.dial.index_colour)
    elif bezel.type == "fluted":
        colour *= (0.7 + 0.3 * (np.sin(theta * 90) > 0))[:, None]
    return colour


# ---------------------------------------------------------------------------------------
# Shading


def _sky(direction: FloatArray, fill: FloatArray) -> FloatArray:
    """What a metal surface reflects: a bright ceiling and a dark room below it."""
    s = np.clip((direction[:, 2] + 0.2) / 0.8, 0, 1)
    s = s * s * (3 - 2 * s)
    floor = np.array([0.04, 0.04, 0.045])
    ceiling = 1.6 * fill
    sky: FloatArray = floor + (ceiling - floor) * s[:, None]
    return sky


def _shade(
    albedo: FloatArray,
    normal: FloatArray,
    view: FloatArray,
    light: FloatArray,
    key: FloatArray,
    fill: FloatArray,
    shadow: FloatArray,
    material: Material,
) -> FloatArray:
    n_dot_l = np.clip(normal @ light, 0, None) * (1 - 0.8 * shadow)
    ambient = fill * (0.55 + 0.45 * np.clip(normal[:, 2], -1, 1))[:, None]
    halfway = light + view
    halfway /= np.linalg.norm(halfway, axis=1, keepdims=True) + 1e-12
    highlight = np.clip(np.sum(normal * halfway, axis=1), 0, None) ** material.shininess
    specular = material.specular * highlight * (1 - shadow)
    if material.metal:
        n_dot_v = np.sum(normal * view, axis=1, keepdims=True)
        reflected = 2 * n_dot_v * normal - view
        colour: FloatArray = albedo * (0.2 * (ambient + key * n_dot_l[:, None]))
        colour += albedo * 0.85 * _sky(reflected, fill)
        colour += albedo * key * specular[:, None]
        return colour
    colour = albedo * (ambient + key * n_dot_l[:, None])
    colour += key * specular[:, None]
    return colour


def _metal_colour(material: str, named: str) -> FloatArray:
    base = {
        "steel": (0.56, 0.57, 0.58),
        "titanium": (0.42, 0.42, 0.44),
        "gold": (0.83, 0.6, 0.28),
        "bronze": (0.55, 0.37, 0.21),
    }.get(material)
    return np.array(base, dtype=float) if base else hex_to_linear(named)


def render(scene: Scene, sample_id: str = "") -> Rendered:
    camera = scene.camera
    height, width = camera.height, camera.width
    geometry = WatchGeometry.from_spec(scene.spec)
    origin = camera.centre
    rays = camera.rays()
    n = len(rays)
    texture_rng = np.random.default_rng([*scene.seed, 7])

    # The surface everything lies on.
    t = -origin[2] / np.where(rays[:, 2] < 0, rays[:, 2], -1e-9)
    kind = np.zeros(n, dtype=np.int64)
    normal = np.tile([0.0, 0.0, 1.0], (n, 1))

    t_arm, kind_arm, normal_arm = _cast_arm(scene, geometry, origin, rays)
    closer = t_arm < t
    t[closer], kind[closer], normal[closer] = t_arm[closer], kind_arm[closer], normal_arm[closer]

    # The watch, only for rays inside its projected bounding box.
    e = geometry.extent
    corners = np.array(
        [
            [su * e, sv * e, w]
            for su in (-1, 1)
            for sv in (-1, 1)
            for w in (0.0, scene.spec.case.thickness_mm)
        ]
    )
    box = camera.project(scene.to_world(corners))
    x0, y0 = np.floor(box.min(axis=0)).astype(int) - 2
    x1, y1 = np.ceil(box.max(axis=0)).astype(int) + 2
    xs, ys = np.meshgrid(
        np.arange(max(0, x0), min(width, x1)), np.arange(max(0, y0), min(height, y1))
    )
    window = (ys * width + xs).ravel()
    watch = _cast_watch(scene, geometry, origin, rays, window)
    closer = watch.t < t[window]
    rows = window[closer]
    t[rows], kind[rows], normal[rows] = watch.t[closer], watch.kind[closer], watch.normal[closer]
    part = np.full(n, -1, dtype=np.int64)
    part[rows] = watch.part[closer]
    uv = np.zeros((n, 2))
    uv[rows] = watch.uv[closer]
    cap = np.zeros(n, dtype=bool)
    cap[rows] = watch.cap[closer]
    inner = np.zeros(n, dtype=bool)
    inner[rows] = watch.inner[closer]

    points = origin + t[:, None] * rays
    view = -rays
    elevation, azimuth = (
        math.radians(scene.light_elevation_deg),
        math.radians(scene.light_azimuth_deg),
    )
    light = np.array(
        [
            math.cos(elevation) * math.cos(azimuth),
            math.cos(elevation) * math.sin(azimuth),
            math.sin(elevation),
        ]
    )
    lighting = LIGHTS[scene.light]
    key = np.array(lighting.key) * scene.light_intensity
    fill = np.array(lighting.fill) * scene.fill_intensity

    # Shadows: does the way to the key light pass through the arm, or under the watch?
    shadow = np.zeros(n)
    low = (kind == 0) | (kind == SKIN) | (kind == STRAP)
    candidates = np.flatnonzero(low)
    lifted = points[candidates] + normal[candidates] * 0.3
    blocked = np.zeros(len(candidates), dtype=bool)
    surface_points = kind[candidates] == 0
    axis_z, radius = _bounds(scene)
    on_floor = candidates[surface_points]
    starts = points[on_floor] + 0.3 * np.array([0.0, 0.0, 1.0])
    enter, leave = _chord(starts, np.tile(light, (len(starts), 1)), axis_z, radius)
    crossing = np.flatnonzero(np.isfinite(enter) & (leave > 0))
    shaded_floor = np.zeros(len(starts), dtype=bool)
    for s in np.linspace(0, 1, 24):
        if len(crossing) == 0:
            break
        along = np.maximum(enter[crossing], 0) + s * (
            leave[crossing] - np.maximum(enter[crossing], 0)
        )
        p = starts[crossing] + along[:, None] * light
        shaded_floor[crossing] |= scene.arm.field(p[:, 0], p[:, 1], p[:, 2]) <= 0
    blocked[surface_points] = shaded_floor
    local = scene.to_watch(lifted)
    ray_local = light @ scene.watch_axes
    mid = 0.5 * scene.spec.case.thickness_mm
    along = (
        (mid - local[:, 2]) / ray_local[2]
        if abs(ray_local[2]) > 1e-6
        else np.full(len(local), -1.0)
    )
    head_u = local[:, 0] + along * ray_local[0]
    head_v = local[:, 1] + along * ray_local[1]
    under = (along > 0) & geometry.case.scaled(1.05).inside(head_u, head_v)
    lug_span = (np.abs(head_u) < scene.spec.lugs.lug_width_mm / 2 + 2.2) & (
        np.abs(head_v) < scene.spec.lugs.lug_to_lug_mm / 2
    )
    blocked |= (along > 0) & (under | lug_span) & ~surface_points
    shadow[candidates] = blocked
    soft = Image.fromarray((shadow.reshape(height, width) * 255).astype(np.uint8))
    soft = soft.filter(ImageFilter.GaussianBlur(radius=max(1.0, width / 400)))
    shadow = np.asarray(soft, dtype=float).ravel() / 255

    colour = np.zeros((n, 3))

    # The surface: grey card, wood or fabric.
    surface = kind == 0
    sp = points[surface]
    albedo = np.tile(scene.surface_colour, (int(surface.sum()), 1))
    if scene.surface == "desk":
        angle = texture_rng.uniform(0, math.pi)
        grain = np.sin((sp[:, 0] * math.cos(angle) + sp[:, 1] * math.sin(angle)) / 2.5)
        albedo *= (0.85 + 0.15 * grain)[:, None]
    elif scene.surface == "fabric":
        weave = np.sin(sp[:, 0] * 5.2) * np.sin(sp[:, 1] * 5.2)
        albedo *= (0.9 + 0.1 * weave)[:, None]
    blotch = _noise(texture_rng, height, width, 12).ravel()
    albedo *= (1 + 0.03 * blotch[surface])[:, None]
    material = MATERIALS[
        "wood" if scene.surface == "desk" else "fabric" if scene.surface == "fabric" else "matte"
    ]
    colour[surface] = _shade(
        albedo, normal[surface], view[surface], light, key, fill, shadow[surface], material
    )

    # Skin.
    skin = kind == SKIN
    skin_albedo = hex_to_linear(MONK_SKIN_TONES[scene.skin_tone - 1])
    mottle = _noise(texture_rng, height, width, 40).ravel()[skin]
    fine = texture_rng.normal(0, 1, int(skin.sum()))
    albedo = (
        np.tile(skin_albedo, (int(skin.sum()), 1)) * (1 + 0.05 * mottle + 0.015 * fine)[:, None]
    )
    colour[skin] = _shade(
        albedo, normal[skin], view[skin], light, key, fill, shadow[skin], MATERIALS["skin"]
    )

    # The strap.
    strap = kind == STRAP
    if strap.any():
        sp = points[strap]
        local = scene.to_watch(sp)
        strap_spec = scene.spec.strap
        albedo = np.tile(hex_to_linear(strap_spec.colour), (len(sp), 1))
        a, b = scene.arm.half_axes(sp[:, 0])
        around = np.arctan2(sp[:, 1] / a, (sp[:, 2] - b) / b) * (a + b) / 2  # arc length, mm
        half = scene.spec.lugs.lug_width_mm / 2
        if strap_spec.type == "bracelet":
            links = np.mod(around, 6.0) < 0.6
            centre = np.abs(local[:, 0]) < half / 3
            albedo = np.tile(
                _metal_colour(scene.spec.case.material, strap_spec.colour), (len(sp), 1)
            )
            albedo *= np.where(links, 0.35, np.where(centre, 1.1, 0.9))[:, None]
            material = MATERIALS["brushed"]
        elif strap_spec.type == "fabric":
            stripe = np.abs(local[:, 0]) < half / 3
            albedo *= np.where(stripe, 1.6, 1.0)[:, None]
            material = MATERIALS["fabric"]
        else:
            stitch = (np.abs(np.abs(local[:, 0]) - (half - 1.0)) < 0.25) & (
                np.mod(around, 3.0) < 1.6
            )
            albedo *= (1 + 0.06 * texture_rng.normal(0, 1, len(sp)))[:, None]
            albedo[stitch] = hex_to_linear("#d8cfc0")
            material = MATERIALS[strap_spec.type if strap_spec.type in MATERIALS else "leather"]
        colour[strap] = _shade(
            albedo, normal[strap], view[strap], light, key, fill, shadow[strap], material
        )

    # The watch.
    case_spec = scene.spec.case
    metal = case_spec.material in ("steel", "titanium", "gold", "bronze")
    case_material = MATERIALS[
        case_spec.finish
        if metal
        else case_spec.material
        if case_spec.material in MATERIALS
        else "resin"
    ]
    case_albedo = _metal_colour(case_spec.material, case_spec.colour)
    for index, solid in enumerate(geometry.solids):
        here = part == index
        if not here.any():
            continue
        count = int(here.sum())
        albedo = np.tile(case_albedo, (count, 1))
        material = case_material
        if solid.kind == "case_low":
            on_dial = kind[here] == DIAL
            albedo[on_dial] = _dial_marks(scene, geometry, uv[here][on_dial])
            shaded = _shade(
                albedo, normal[here], view[here], light, key, fill, shadow[here], case_material
            )
            dial_shaded = _shade(
                albedo[on_dial],
                normal[here][on_dial],
                view[here][on_dial],
                light,
                key,
                fill,
                shadow[here][on_dial],
                MATERIALS["dial"],
            )
            shaded[on_dial] = dial_shaded
            # The crystal: a faint reflection of the room, and a sharp highlight.
            crystal = np.tile([0.0, 0.0, 1.0], (int(on_dial.sum()), 1)) @ scene.watch_axes.T
            v_d = view[here][on_dial]
            reflected = 2 * np.sum(crystal * v_d, axis=1, keepdims=True) * crystal - v_d
            glint = np.clip(np.sum(reflected * light, axis=1), 0, None) ** 300
            shaded[on_dial] += 0.04 * _sky(reflected, fill) + 3.0 * glint[:, None] * key
            colour[here] = shaded
            continue
        if solid.kind == "case_high":
            rehaut = inner[here]
            albedo[rehaut] = 0.6 * hex_to_linear(scene.spec.dial.colour) + 0.1
        if solid.kind == "bezel":
            bezel = scene.spec.bezel
            on_top = cap[here]
            if bezel.insert_colour is not None:
                insert = np.tile(hex_to_linear(bezel.insert_colour), (int(on_top.sum()), 1))
                albedo[on_top] = _bezel_marks(scene, geometry, uv[here][on_top], insert)
                top_shaded = _shade(
                    albedo[on_top],
                    normal[here][on_top],
                    view[here][on_top],
                    light,
                    key,
                    fill,
                    shadow[here][on_top],
                    MATERIALS["insert"],
                )
                shaded = _shade(
                    albedo, normal[here], view[here], light, key, fill, shadow[here], material
                )
                shaded[on_top] = top_shaded
                colour[here] = shaded
                continue
            albedo[on_top] = _bezel_marks(scene, geometry, uv[here][on_top], albedo[on_top])
        colour[here] = _shade(
            albedo, normal[here], view[here], light, key, fill, shadow[here], material
        )

    # The camera: exposure, vignetting, blur, noise.
    luminance = colour @ np.array([0.2126, 0.7152, 0.0722])
    reference = luminance[surface] if surface.sum() > n // 20 else luminance
    gain = scene.post.exposure / max(float(np.median(reference)), 1e-6)
    image = (colour * gain).reshape(height, width, 3)
    yy, xx = np.mgrid[0:height, 0:width]
    radius = np.hypot((xx - width / 2) / (width / 2), (yy - height / 2) / (height / 2)) / math.sqrt(
        2
    )
    image *= (1 - scene.post.vignette * radius**2)[:, :, None]
    encoded = Image.fromarray((linear_to_srgb(image) * 255 + 0.5).astype(np.uint8))
    encoded = encoded.filter(ImageFilter.GaussianBlur(radius=scene.post.blur_px * width / 1024))
    pixels = np.asarray(encoded, dtype=float)
    pixels += texture_rng.normal(0, scene.post.noise, pixels.shape)
    final = np.clip(pixels + 0.5, 0, 255).astype(np.uint8)
    classes = kind.reshape(height, width).astype(np.uint8)
    return Rendered(
        image=final, classes=classes, labels=_labels(scene, geometry, classes, sample_id)
    )


# ---------------------------------------------------------------------------------------
# Labels


def _outline(scene: Scene, outline: Outline, height: float) -> list[list[float]]:
    boundary = outline.boundary(180)
    local = np.column_stack([boundary, np.full(len(boundary), height)])
    projected = scene.camera.project(scene.to_world(local))
    return [[round(float(x), 3), round(float(y), 3)] for x, y in projected]


def _wrist_edges(scene: Scene, classes: npt.NDArray[np.uint8]) -> list[list[float]] | None:
    """Where the forearm's silhouette crosses the image line through the watch, across the arm."""
    camera = scene.camera
    centre, along = camera.project(
        np.array([scene.watch_origin, scene.watch_origin + np.array([10.0, 0, 0])])
    )
    direction = along - centre
    across = np.array([-direction[1], direction[0]]) / (np.linalg.norm(direction) + 1e-12)
    steps = np.arange(-camera.width, camera.width, 0.5)
    line = centre + steps[:, None] * across
    x, y = np.floor(line[:, 0]).astype(int), np.floor(line[:, 1]).astype(int)
    valid = (x >= 0) & (x < camera.width) & (y >= 0) & (y < camera.height)
    on_arm = np.zeros(len(steps), dtype=bool)
    on_arm[valid] = classes[y[valid], x[valid]] > 0
    middle = len(steps) // 2
    if not on_arm[middle]:
        return None
    off = np.flatnonzero(~on_arm)
    before, after = off[off < middle], off[off > middle]
    if len(before) == 0 or len(after) == 0 or not valid[before[-1]] or not valid[after[0]]:
        return None  # the silhouette runs off the image
    return [
        [round(float(v), 2) for v in line[before[-1] + 1]],
        [round(float(v), 2) for v in line[after[0] - 1]],
    ]


def _labels(
    scene: Scene, geometry: WatchGeometry, classes: npt.NDArray[np.uint8], sample_id: str
) -> SyntheticLabels:
    camera = scene.camera
    outlines = Outlines(
        case_top=_outline(scene, geometry.case, geometry.case_top),
        case_back=_outline(scene, geometry.case, 0.0),
        bezel_top=None
        if geometry.bezel is None
        else _outline(scene, geometry.bezel, geometry.bezel_top),
        opening_top=_outline(scene, geometry.opening, geometry.bezel_top),
        dial=_outline(scene, geometry.opening, geometry.dial_height),
    )
    top_centre = scene.to_world(np.array([[0.0, 0.0, geometry.case_top]]))[0]
    depth = float(camera.to_camera(top_centre[None, :])[0, 2])
    circle = ellipse = None
    if scene.spec.case.shape == "round":
        circle = ReferenceCircle(
            centre=[float(v) for v in top_centre],
            normal=[float(v) for v in scene.watch_axes[:, 2]],
            radius_mm=geometry.case.a,
        )
        fitted = fit_ellipse(np.array(outlines.case_top))
        ellipse = ImageEllipse(
            cx=fitted.cx, cy=fitted.cy, a=fitted.a, b=fitted.b, angle=fitted.angle
        )
    counts = np.bincount(classes.ravel(), minlength=6)
    return SyntheticLabels(
        sample_id=sample_id,
        generator=f"lugtolug-ml {__version__} synthetic v0",
        seed=list(scene.seed),
        camera=CameraLabel(
            width=camera.width,
            height=camera.height,
            fx=camera.fx,
            fy=camera.fy,
            cx=camera.cx,
            cy=camera.cy,
            rotation=[[float(v) for v in row] for row in camera.rotation],
            translation=[float(v) for v in camera.translation],
        ),
        watch=WatchPose(
            origin=[float(v) for v in scene.watch_origin],
            u=[float(v) for v in scene.watch_axes[:, 0]],
            v=[float(v) for v in scene.watch_axes[:, 1]],
            w=[float(v) for v in scene.watch_axes[:, 2]],
        ),
        spec=scene.spec,
        heights_mm=Heights(
            dial=geometry.dial_height,
            case_top=geometry.case_top,
            bezel_top=geometry.bezel_top,
            thickness=scene.spec.case.thickness_mm,
        ),
        outlines=outlines,
        reference_circle=circle,
        case_top_ellipse=ellipse,
        px_per_mm=camera.fx / depth,
        wrist=WristLabel(
            width_mm=scene.arm.width_mm,
            thickness_mm=scene.arm.thickness_mm,
            circumference_mm=scene.arm.circumference_mm,
            hand_breadth_mm=scene.arm.hand_breadth_mm,
            edges=_wrist_edges(scene, classes),
        ),
        conditions=Conditions(
            skin_tone=scene.skin_tone,
            light=scene.light,
            light_elevation_deg=scene.light_elevation_deg,
            light_azimuth_deg=scene.light_azimuth_deg,
            surface=scene.surface,
            tilt_deg=scene.tilt_deg,
            roll_deg=scene.roll_deg,
            distance_mm=scene.distance_mm,
            crown_towards_hand=scene.crown_towards_hand,
            dial_time=scene.dial_time,
            blur_px=scene.post.blur_px,
            noise=scene.post.noise,
            vignette=scene.post.vignette,
            jpeg_quality=scene.post.jpeg_quality,
        ),
        pixel_counts={i: int(c) for i, c in enumerate(counts) if c},
    )
