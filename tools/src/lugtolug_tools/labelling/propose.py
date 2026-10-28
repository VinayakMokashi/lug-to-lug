"""A first guess at the case outline, for a person to accept or correct.

The person clicks the middle of the case, then a point on its edge. From the middle,
rays run outwards. Along each, the outermost strong change in brightness near the
clicked radius is a candidate, since the case's edge against the wrist is outside the
dial's edge. A RANSAC ellipse fit keeps the candidates that agree with each other,
dropping the lugs and strap, and the proposal is those points.

A simple baseline, named and versioned in every label it proposes. Phase 2 measures it
against trained models.
"""

from __future__ import annotations

import math

import numpy as np

from lugtolug_core.geometry import Ellipse, FloatArray, fit_ellipse

PROPOSER = "radial-edge-ellipse 0.1"
# A ray counts only if its brightness changes by at least this much per pixel somewhere:
# on a blank stretch every ray's "strongest" change is noise, and they would line up.
MIN_CONTRAST = 2.0


def _sample(image: FloatArray, xs: FloatArray, ys: FloatArray) -> FloatArray:
    """Bilinear samples of a 2-D array at (x, y) image coordinates (pixel centres at .5)."""
    height, width = image.shape
    x = np.clip(xs - 0.5, 0, width - 1.001)
    y = np.clip(ys - 0.5, 0, height - 1.001)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    top = image[y0, x0] * (1 - fx) + image[y0, x0 + 1] * fx
    bottom = image[y0 + 1, x0] * (1 - fx) + image[y0 + 1, x0 + 1] * fx
    values: FloatArray = top * (1 - fy) + bottom * fy
    return values


def _radius_along(ellipse: Ellipse, cx: float, cy: float, angles: FloatArray) -> FloatArray:
    """How far rays from (cx, cy) travel before meeting the ellipse."""
    cos, sin = math.cos(ellipse.angle), math.sin(ellipse.angle)
    ox, oy = cx - ellipse.cx, cy - ellipse.cy
    px, py = ox * cos + oy * sin, -ox * sin + oy * cos
    dx = np.cos(angles) * cos + np.sin(angles) * sin
    dy = -np.cos(angles) * sin + np.sin(angles) * cos
    a2, b2 = ellipse.a**2, ellipse.b**2
    qa = dx**2 / a2 + dy**2 / b2
    qb = 2 * (px * dx / a2 + py * dy / b2)
    qc = px**2 / a2 + py**2 / b2 - 1
    root = np.sqrt(np.maximum(qb**2 - 4 * qa * qc, 0))
    along: FloatArray = (-qb + root) / (2 * qa)
    return along


def propose_case_outline(
    grey: FloatArray,
    centre: tuple[float, float],
    edge: tuple[float, float],
    *,
    rays: int = 72,
    seed: int = 0,
) -> list[tuple[float, float]]:
    """Points on the case's outer edge, or an empty list when no ellipse stands out.

    `grey` is the image as a 2-D brightness array; `centre` and `edge` are the person's
    two clicks.
    """
    cx, cy = centre
    r0 = math.hypot(edge[0] - cx, edge[1] - cy)
    if r0 < 5:
        return []
    angles = np.linspace(0, 2 * math.pi, rays, endpoint=False)
    radii = np.arange(0.6 * r0, 1.25 * r0, 0.5)
    xs = cx + np.outer(np.cos(angles), radii)
    ys = cy + np.outer(np.sin(angles), radii)
    profile = _sample(grey, xs.ravel(), ys.ravel()).reshape(xs.shape)
    change = np.abs(np.gradient(profile, axis=1))
    change = (change + np.roll(change, 1, axis=1) + np.roll(change, -1, axis=1)) / 3
    strongest = change.max(axis=1, keepdims=True)
    strong = change >= 0.5 * np.maximum(strongest, 1e-9)
    outermost = strong.shape[1] - 1 - np.argmax(strong[:, ::-1], axis=1)
    candidates = np.column_stack(
        [cx + np.cos(angles) * radii[outermost], cy + np.sin(angles) * radii[outermost]]
    )
    found = radii[outermost]
    usable = strongest[:, 0] >= MIN_CONTRAST

    rng = np.random.default_rng(seed)
    best: FloatArray | None = None
    best_count = 0
    tolerance = max(1.5, 0.02 * r0)
    if usable.sum() < max(8, rays // 3):
        return []
    for _ in range(300):
        pick = rng.choice(np.flatnonzero(usable), size=5, replace=False)
        try:
            trial = fit_ellipse(candidates[pick])
        except ValueError:
            continue
        if trial.a > 2 * r0 or trial.b < 0.3 * r0:
            continue
        inliers = usable & (np.abs(_radius_along(trial, cx, cy, angles) - found) < tolerance)
        if inliers.sum() > best_count:
            best, best_count = inliers, int(inliers.sum())
    if best is None or best_count < max(8, rays // 3):
        return []
    try:
        final = fit_ellipse(candidates[best])
    except ValueError:
        return []
    keep = usable & (np.abs(_radius_along(final, cx, cy, angles) - found) < tolerance)
    return [(float(x), float(y)) for x, y in candidates[keep]]
