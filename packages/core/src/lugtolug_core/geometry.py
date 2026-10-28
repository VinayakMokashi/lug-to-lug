"""Camera geometry shared by calibration, the synthetic data and the labelling tool.

Conventions, as in OpenCV:

- image x to the right and y down, with (0, 0) at the top-left corner of the top-left
  pixel, so pixel (i, j) has its centre at (i + 0.5, j + 0.5);
- the camera looks along its +z axis, with x to the right and y down;
- a world point X maps into the camera as R @ X + t.

Lengths are in millimetres.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]

# The Pixel 9a's main camera: a 6.4 x 4.8 mm sensor read out at 4000 x 3000 (1.6 um
# pixels) behind a 4.53 mm lens, so about 2831 px of focal length and a horizontal field
# of view of about 70.5 degrees. A planning value until the camera is calibrated.
PIXEL_9A_SIZE = (4000, 3000)
PIXEL_9A_FOCAL_MM = 4.53
PIXEL_9A_PIXEL_MM = 6.4 / 4000


@dataclass(frozen=True, eq=False)
class Camera:
    """A pinhole camera: intrinsics plus the world-to-camera pose."""

    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    rotation: FloatArray = field(default_factory=lambda: np.eye(3))
    translation: FloatArray = field(default_factory=lambda: np.zeros(3))

    @classmethod
    def pixel_9a(cls, width: int = PIXEL_9A_SIZE[0]) -> Camera:
        """The Pixel 9a's main camera at 1x, scaled to an image `width` pixels wide."""
        scale = width / PIXEL_9A_SIZE[0]
        focal = PIXEL_9A_FOCAL_MM / PIXEL_9A_PIXEL_MM * scale
        height = round(PIXEL_9A_SIZE[1] * scale)
        return cls(width, height, focal, focal, width / 2, height / 2)

    @property
    def matrix(self) -> FloatArray:
        return np.array([[self.fx, 0, self.cx], [0, self.fy, self.cy], [0, 0, 1]], dtype=float)

    @property
    def centre(self) -> FloatArray:
        """Where the camera is, in world coordinates."""
        centre: FloatArray = -self.rotation.T @ self.translation
        return centre

    def looking_at(self, eye: FloatArray, target: FloatArray, up: FloatArray) -> Camera:
        """The same camera placed at `eye` and aimed at `target`, with `up` pointing up."""
        forward = _unit(np.asarray(target, float) - np.asarray(eye, float))
        right = _unit(np.cross(forward, np.asarray(up, float)))
        down = np.cross(forward, right)
        rotation = np.stack([right, down, forward])
        return replace(self, rotation=rotation, translation=-rotation @ np.asarray(eye, float))

    def to_camera(self, points: FloatArray) -> FloatArray:
        moved: FloatArray = np.asarray(points, float) @ self.rotation.T + self.translation
        return moved

    def project(self, points: FloatArray) -> FloatArray:
        """Image coordinates of world points (N x 3 -> N x 2)."""
        cam = self.to_camera(points)
        pixels: FloatArray = np.column_stack(
            [self.fx * cam[:, 0] / cam[:, 2] + self.cx, self.fy * cam[:, 1] / cam[:, 2] + self.cy]
        )
        return pixels

    def rays(self, pixels: FloatArray | None = None) -> FloatArray:
        """Unit world directions through image points, by default every pixel's centre.

        Without `pixels` the result is (height * width) x 3, row by row.
        """
        if pixels is None:
            xs = np.arange(self.width) + 0.5
            ys = np.arange(self.height) + 0.5
            grid_x, grid_y = np.meshgrid(xs, ys)
            pixels = np.column_stack([grid_x.ravel(), grid_y.ravel()])
        cam = np.column_stack(
            [
                (pixels[:, 0] - self.cx) / self.fx,
                (pixels[:, 1] - self.cy) / self.fy,
                np.ones(len(pixels)),
            ]
        )
        world = cam @ self.rotation  # the inverse rotation, applied to row vectors
        unit: FloatArray = world / np.linalg.norm(world, axis=1, keepdims=True)
        return unit


def _unit(vector: FloatArray) -> FloatArray:
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        raise ValueError("a direction can't be zero")
    unit: FloatArray = vector / norm
    return unit


@dataclass(frozen=True)
class Ellipse:
    """An ellipse in the image: centre, semi-axes (a >= b) and the major axis's angle.

    The angle is in radians from the image x axis towards the image y axis (clockwise on
    screen, because y points down).
    """

    cx: float
    cy: float
    a: float
    b: float
    angle: float

    def points(self, n: int = 72) -> FloatArray:
        t = np.linspace(0, 2 * math.pi, n, endpoint=False)
        cos, sin = math.cos(self.angle), math.sin(self.angle)
        x = self.cx + self.a * np.cos(t) * cos - self.b * np.sin(t) * sin
        y = self.cy + self.a * np.cos(t) * sin + self.b * np.sin(t) * cos
        stacked: FloatArray = np.column_stack([x, y])
        return stacked

    @classmethod
    def from_conic(cls, conic: FloatArray) -> Ellipse:
        """The ellipse A x^2 + B xy + C y^2 + D x + E y + F = 0, given (A, B, C, D, E, F)."""
        a, b, c, d, e, f = (float(v) for v in conic)
        if b * b - 4 * a * c >= 0:
            raise ValueError("the conic is not an ellipse")
        x0, y0 = np.linalg.solve(np.array([[2 * a, b], [b, 2 * c]]), np.array([-d, -e]))
        value_at_centre = f + (d * x0 + e * y0) / 2
        quadratic = np.array([[a, b / 2], [b / 2, c]])
        values, vectors = np.linalg.eigh(quadratic)
        semi = np.sqrt(-value_at_centre / values)
        if not np.all(np.isfinite(semi)):
            raise ValueError("the conic is an imaginary ellipse")
        major = int(np.argmax(semi))
        vx, vy = vectors[:, major]
        angle = math.atan2(vy, vx) % math.pi
        return cls(float(x0), float(y0), float(semi.max()), float(semi.min()), angle)


def fit_ellipse(points: FloatArray) -> Ellipse:
    """The least-squares ellipse through image points.

    Fitzgibbon's direct method in the numerically stable form of Halir and Flusser
    (1998), on coordinates centred and scaled first. Five points determine an ellipse;
    more average out noise.
    """
    points = np.asarray(points, float)
    if len(points) < 5:
        raise ValueError("an ellipse needs at least five points")
    mean = points.mean(axis=0)
    scale = float(points.std(axis=0).max())
    if scale == 0:
        raise ValueError("the points are all the same")
    x, y = ((points - mean) / scale).T
    d1 = np.column_stack([x * x, x * y, y * y])
    d2 = np.column_stack([x, y, np.ones_like(x)])
    s1, s2, s3 = d1.T @ d1, d1.T @ d2, d2.T @ d2
    try:
        t = -np.linalg.solve(s3, s2.T)
    except np.linalg.LinAlgError:
        raise ValueError("the points don't determine an ellipse") from None
    m = s1 + s2 @ t
    m = np.array([m[2] / 2, -m[1], m[0] / 2])
    _, vectors = np.linalg.eig(m)
    vectors = np.real(vectors)
    condition = 4 * vectors[0] * vectors[2] - vectors[1] ** 2
    candidates = np.flatnonzero(condition > 0)
    if len(candidates) == 0:
        raise ValueError("the points don't determine an ellipse")
    top = vectors[:, candidates[0]]
    a, b, c, d, e, f = np.concatenate([top, t @ top])
    # Undo the centring and scaling: x' = (x - mx) / s, y' = (y - my) / s.
    mx, my = mean
    s = scale
    conic = np.array(
        [
            a,
            b,
            c,
            -2 * a * mx - b * my + d * s,
            -b * mx - 2 * c * my + e * s,
            a * mx * mx + b * mx * my + c * my * my - d * s * mx - e * s * my + f * s * s,
        ]
    )
    return Ellipse.from_conic(conic)
