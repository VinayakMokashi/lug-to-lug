"""What a synthetic photo shows: a forearm on a surface, a watch on it, a camera, a light.

World coordinates are in millimetres: the surface is the plane z = 0, the forearm lies
along the x axis with the hand towards +x, and the watch sits on top of the wrist at
x = 0. The watch has its own frame: u towards 3 o'clock, v towards 12 o'clock, w out of
the dial, with its origin at the centre of the case back.

Every random choice comes from one seeded generator, so a sample is reproduced exactly
from its seed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from lugtolug_core.contracts.stand_in import StandInSpec
from lugtolug_core.geometry import Camera, FloatArray
from lugtolug_core.standin import Appearance, Dimensions, build_spec, check_spec
from lugtolug_core.vocab import BezelType, CaseMaterial, CaseShape, ColourName, StrapType

BoolArray = npt.NDArray[np.bool_]
LIGHT_CONDITIONS = ("DAY", "WARM", "MIX")
SURFACES = ("backdrop", "desk", "fabric")


# ---------------------------------------------------------------------------------------
# Shapes in the watch's plane


@dataclass(frozen=True)
class Outline:
    """A superellipse: half-width `a` along u, half-length `b` along v, exponent `n`.

    `taper` narrows it towards 12 and 6 o'clock (1 for none), which makes a tonneau.
    """

    a: float
    b: float
    n: float = 2.0
    taper: float = 1.0

    def scaled(self, factor: float) -> Outline:
        return Outline(self.a * factor, self.b * factor, self.n, self.taper)

    def _half_width(self, v: FloatArray) -> FloatArray:
        along: FloatArray = np.clip(v / self.b, -1, 1)
        half: FloatArray = self.a * (1 - (1 - self.taper) * along**2)
        return half

    def inside(self, u: FloatArray, v: FloatArray) -> BoolArray:
        result: BoolArray = (np.abs(u / self._half_width(v)) ** self.n) + (
            np.abs(v / self.b) ** self.n
        ) <= 1
        return result

    def normal(self, u: FloatArray, v: FloatArray) -> FloatArray:
        """Unit outward normals in the plane at points on (or near) the outline."""
        gu = np.sign(u) * np.abs(u / self._half_width(v)) ** (self.n - 1) / self._half_width(v)
        gv = np.sign(v) * np.abs(v / self.b) ** (self.n - 1) / self.b
        normals = np.stack([gu, gv], axis=-1)
        length = np.linalg.norm(normals, axis=-1, keepdims=True)
        unit: FloatArray = normals / np.where(length == 0, 1, length)
        return unit

    def boundary(self, count: int = 180) -> FloatArray:
        """Points around the outline, counter-clockwise from 3 o'clock."""
        t = np.linspace(0, 2 * math.pi, count, endpoint=False)
        cos, sin = np.cos(t), np.sin(t)
        v = self.b * np.sign(sin) * np.abs(sin) ** (2 / self.n)
        u = self._half_width(v) * np.sign(cos) * np.abs(cos) ** (2 / self.n)
        points: FloatArray = np.column_stack([u, v])
        return points


@dataclass(frozen=True)
class Box:
    """A rectangle in the watch's plane, centred at (u, v) and turned by `angle` radians."""

    u: float
    v: float
    half_u: float
    half_v: float
    angle: float = 0.0

    def _local(self, u: FloatArray, v: FloatArray) -> tuple[FloatArray, FloatArray]:
        cos, sin = math.cos(self.angle), math.sin(self.angle)
        du, dv = u - self.u, v - self.v
        return du * cos + dv * sin, -du * sin + dv * cos

    def inside(self, u: FloatArray, v: FloatArray) -> BoolArray:
        lu, lv = self._local(u, v)
        result: BoolArray = (np.abs(lu) <= self.half_u) & (np.abs(lv) <= self.half_v)
        return result

    def normal(self, u: FloatArray, v: FloatArray) -> FloatArray:
        lu, lv = self._local(u, v)
        on_u = np.abs(lu) / self.half_u >= np.abs(lv) / self.half_v
        nu = np.where(on_u, np.sign(lu), 0.0)
        nv = np.where(on_u, 0.0, np.sign(lv))
        cos, sin = math.cos(self.angle), math.sin(self.angle)
        normals: FloatArray = np.stack([nu * cos - nv * sin, nu * sin + nv * cos], axis=-1)
        return normals


@dataclass(frozen=True)
class Solid:
    """A prism between two heights above the case back, optionally with a hole."""

    kind: str  # case_low, case_high, bezel, lug, crown
    outer: Outline | Box
    bottom: float
    top: float
    hole: Outline | None = None


@dataclass(frozen=True)
class WatchGeometry:
    """The watch's solids, and the heights of its edges, from its stand-in spec."""

    spec: StandInSpec
    case: Outline
    bezel: Outline | None
    opening: Outline
    dial_height: float  # the dial's surface
    case_top: float  # the case body's top edge
    bezel_top: float  # the bezel's top edge, or the case top when there's no bezel
    solids: tuple[Solid, ...]

    @classmethod
    def from_spec(cls, spec: StandInSpec) -> WatchGeometry:
        c = spec.case
        case = Outline(c.diameter_mm / 2, c.length_mm / 2, c.squareness, c.taper)
        opening = case.scaled(spec.dial.opening_mm / c.diameter_mm)
        thickness = c.thickness_mm
        case_top = 0.62 * thickness
        dial_height = case_top - max(0.6, 0.12 * thickness)
        bezel = None
        bezel_top = case_top
        solids = [
            Solid("case_low", case, 0.0, dial_height),
            Solid("case_high", case, dial_height, case_top, hole=opening),
        ]
        if spec.bezel.outer_mm is not None:
            bezel = case.scaled(spec.bezel.outer_mm / c.diameter_mm)
            bezel_top = case_top + max(0.8, 0.12 * thickness)
            solids.append(Solid("bezel", bezel, case_top, bezel_top, hole=opening))

        lugs = spec.lugs
        half_gap = lugs.lug_width_mm / 2
        lug_half_u = 1.1
        tip = lugs.lug_to_lug_mm / 2
        root = max(case.b - 3.0, 0.5 * case.b)
        for su in (-1, 1):
            for sv in (-1, 1):
                box = Box(
                    u=su * (half_gap + lug_half_u),
                    v=sv * (root + tip) / 2,
                    half_u=lug_half_u,
                    half_v=(tip - root) / 2,
                )
                solids.append(Solid("lug", box, 0.12 * thickness, 0.55 * thickness))

        crown = spec.crown
        angle = math.radians((3 - crown.position) * 30)
        radius = crown.diameter_mm / 2
        reach = case.a + crown.length_mm / 2 - 0.25
        box = Box(
            u=reach * math.cos(angle),
            v=reach * math.sin(angle) * case.b / case.a,
            half_u=crown.length_mm / 2 + 0.25,
            half_v=radius,
            angle=angle,
        )
        centre = 0.35 * thickness
        solids.append(Solid("crown", box, max(0.0, centre - radius), centre + radius))
        return cls(spec, case, bezel, opening, dial_height, case_top, bezel_top, tuple(solids))

    @property
    def extent(self) -> float:
        """Half the size of a box around everything in the watch's plane."""
        return max(self.spec.lugs.lug_to_lug_mm / 2, self.case.a + self.spec.crown.length_mm) + 2


# ---------------------------------------------------------------------------------------
# The forearm and hand


@dataclass(frozen=True)
class Arm:
    """A forearm resting on the surface, narrowing into a hand at +x.

    It is an implicit surface: field() is negative inside. Across the forearm the
    section is an ellipse of half-width a and half-height b, resting on z = 0. Past the
    wrist it narrows smoothly into the hand, so there is no seam.
    """

    width_mm: float  # at the watch
    thickness_mm: float
    hand_breadth_mm: float
    hand_thickness_mm: float = 26.0
    hand_start_mm: float = 45.0  # where the narrowing ends, past the watch
    hand_length_mm: float = 175.0

    def half_axes(self, x: FloatArray) -> tuple[FloatArray, FloatArray]:
        a0, b0 = self.width_mm / 2, self.thickness_mm / 2
        elbow = np.maximum(0.0, -x)
        a = a0 * (1 + 0.0011 * elbow)  # wider towards the elbow
        b = b0 * (1 + 0.0004 * elbow)
        s = np.clip((x - 20) / (self.hand_start_mm + 30 - 20), 0, 1)
        blend = s * s * (3 - 2 * s)
        a = a + (self.hand_breadth_mm / 2 - a) * blend
        b = b + (self.hand_thickness_mm / 2 - b) * blend
        return a, b

    def field(
        self, x: FloatArray, y: FloatArray, z: FloatArray, grow: float | FloatArray = 0.0
    ) -> FloatArray:
        """Negative inside the forearm and hand, grown outwards by `grow` mm."""
        a, b = self.half_axes(x)
        a, b = a + grow, b + grow
        forearm = (y / a) ** 2 + ((z - (b - grow)) / b) ** 2 - 1
        end = self.hand_start_mm + 30 + self.hand_length_mm
        # The hand ends in a rounded tip: an ellipsoid cap past `end`.
        tip = np.maximum(0.0, x - end) / (35.0 + grow)
        value: FloatArray = forearm + tip**2
        return value

    def top(self, x: float = 0.0) -> float:
        _, b = self.half_axes(np.array([x]))
        return float(2 * b[0])

    @property
    def circumference_mm(self) -> float:
        a, b = self.width_mm / 2, self.thickness_mm / 2
        return math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))  # Ramanujan


# ---------------------------------------------------------------------------------------
# A whole scene


@dataclass(frozen=True)
class Post:
    """What the camera does to the image after the light: blur, noise, compression."""

    exposure: float  # the backdrop's target brightness, in linear light
    blur_px: float
    noise: float  # standard deviation on the 0-255 scale
    vignette: float
    jpeg_quality: int


@dataclass(frozen=True, eq=False)
class Scene:
    spec: StandInSpec
    arm: Arm
    skin_tone: int  # 1-10 on the Monk Skin Tone Scale
    camera: Camera
    watch_origin: FloatArray  # the centre of the case back, in world coordinates
    watch_axes: FloatArray  # columns: u (3 o'clock), v (12 o'clock), w (out of the dial)
    light: str
    light_elevation_deg: float
    light_azimuth_deg: float
    light_intensity: float
    fill_intensity: float
    surface: str
    surface_colour: FloatArray  # linear RGB
    dial_time: tuple[int, int, int]
    tilt_deg: float
    roll_deg: float
    distance_mm: float
    crown_towards_hand: bool
    post: Post
    seed: tuple[int, ...]

    def to_watch(self, points: FloatArray) -> FloatArray:
        local: FloatArray = (np.asarray(points, float) - self.watch_origin) @ self.watch_axes
        return local

    def to_world(self, local: FloatArray) -> FloatArray:
        world: FloatArray = np.asarray(local, float) @ self.watch_axes.T + self.watch_origin
        return world


_SHAPES: tuple[CaseShape, ...] = ("round", "cushion", "tonneau", "square", "other")
_SHAPE_WEIGHTS = (0.7, 0.1, 0.05, 0.1, 0.05)
_BEZELS: tuple[BezelType, ...] = ("none", "smooth", "fluted", "rotating_insert", "other")
_BEZEL_WEIGHTS = (0.2, 0.3, 0.1, 0.35, 0.05)
_MATERIALS: tuple[CaseMaterial, ...] = ("steel", "titanium", "gold", "ceramic", "resin", "bronze")
_MATERIAL_WEIGHTS = (0.6, 0.1, 0.1, 0.07, 0.08, 0.05)
_DIALS: tuple[ColourName, ...] = (
    "black", "white", "silver", "grey", "blue", "green", "red", "brown",
    "champagne", "cream", "orange", "yellow", "pink", "purple",
)  # fmt: skip
_STRAPS: tuple[StrapType, ...] = ("bracelet", "leather", "rubber", "fabric")
_STRAP_WEIGHTS = (0.4, 0.3, 0.2, 0.1)


def _choice[T](
    rng: np.random.Generator, options: tuple[T, ...], weights: tuple[float, ...] | None = None
) -> T:
    p = None if weights is None else np.array(weights) / sum(weights)
    return options[int(rng.choice(len(options), p=p))]


def sample_spec(rng: np.random.Generator) -> StandInSpec:
    """A plausible watch: every dimension known, so nothing in it is assumed."""
    while True:
        shape = _choice(rng, _SHAPES, _SHAPE_WEIGHTS)
        diameter = float(rng.uniform(26, 33) if shape == "square" else rng.uniform(30, 46))
        length = None if shape == "round" else diameter * float(rng.uniform(1.0, 1.35))
        bezel_type = _choice(rng, _BEZELS, _BEZEL_WEIGHTS)
        opening_ratio = {"none": 0.88, "smooth": 0.82, "fluted": 0.8, "rotating_insert": 0.74}.get(
            bezel_type, 0.8
        )
        span = (length or diameter) * float(rng.uniform(1.1, 1.3))
        dims = Dimensions(
            case_shape=shape,
            case_diameter_mm=round(diameter, 2),
            case_length_mm=None if length is None else round(length, 2),
            bezel_diameter_mm=round(diameter * float(rng.uniform(0.97, 1.02)), 2),
            dial_opening_mm=round(diameter * opening_ratio * float(rng.uniform(0.95, 1.04)), 2),
            lug_to_lug_mm=round(span, 2),
            thickness_mm=round(float(rng.uniform(7, 16)), 2),
            lug_width_mm=float(2 * round(diameter * float(rng.uniform(0.44, 0.56)) / 2)),
            crown_position=int(_choice(rng, (3, 3, 3, 3, 4, 9))),
        )
        look = Appearance(
            bezel_type=bezel_type,
            case_material=_choice(rng, _MATERIALS, _MATERIAL_WEIGHTS),
            dial_colour=_choice(rng, _DIALS),
            strap_type=_choice(rng, _STRAPS, _STRAP_WEIGHTS),
        )
        spec = build_spec(dims, look)
        if not check_spec(spec):
            return spec


def sample_scene(
    rng: np.random.Generator,
    width: int,
    seed: tuple[int, ...] = (),
    tilt_deg: float | None = None,
) -> Scene:
    """A random scene; `tilt_deg` fixes the camera's tilt (tests use it)."""
    spec = sample_spec(rng)
    arm = Arm(
        width_mm=float(rng.uniform(48, 72)),
        thickness_mm=float(rng.uniform(34, 50)),
        hand_breadth_mm=float(rng.uniform(70, 95)),
    )
    skin_tone = int(rng.integers(1, 11))

    # The watch sits on top of the wrist, rolled a little around the arm.
    roll = float(rng.normal(0, 4))
    a, b = arm.width_mm / 2, arm.thickness_mm / 2
    phi = math.radians(roll)
    origin = np.array([0.0, a * math.sin(phi), b + b * math.cos(phi)])
    w_axis = np.array([0.0, math.sin(phi) / a, math.cos(phi) / b])
    w_axis /= np.linalg.norm(w_axis)
    crown_towards_hand = bool(rng.random() < 0.8)
    yaw = math.radians(float(rng.normal(0, 4)))
    u_axis = np.array([math.cos(yaw), math.sin(yaw), 0.0]) * (1 if crown_towards_hand else -1)
    u_axis -= w_axis * float(u_axis @ w_axis)
    u_axis /= np.linalg.norm(u_axis)
    v_axis = np.cross(w_axis, u_axis)
    axes = np.column_stack([u_axis, v_axis, w_axis])

    # The camera tilts around the arm's long axis, about 30 cm above the watch.
    tilt = float(rng.uniform(0, 45)) * (1 if rng.random() < 0.5 else -1)
    if tilt_deg is not None:
        tilt = tilt_deg
    distance = float(rng.uniform(250, 400))
    t = math.radians(tilt)
    view = np.array([0.0, math.sin(t), math.cos(t)])
    top = origin + w_axis * spec.case.thickness_mm
    target = top + np.array([rng.normal(0, 12), rng.normal(0, 8), 0.0])
    eye = top + view * distance
    up = np.array([0.0, math.cos(t), -math.sin(t)])
    spin = math.radians(float(rng.uniform(-20, 20)) + (180 if rng.random() < 0.5 else 0))
    right = np.cross(view, up)
    up = up * math.cos(spin) + right * math.sin(spin)
    camera = Camera.pixel_9a(width).looking_at(eye, target, up)

    surface = _choice(rng, SURFACES, (0.6, 0.25, 0.15))
    grey = float(rng.uniform(0.17, 0.24))
    colours = {
        "backdrop": np.array([grey, grey, grey * 1.02]),
        "desk": np.array([0.35, 0.2, 0.1]) * float(rng.uniform(0.5, 1.4)),
        "fabric": rng.uniform(0.05, 0.4, 3),
    }
    seconds = int(rng.integers(0, 43200))
    return Scene(
        spec=spec,
        arm=arm,
        skin_tone=skin_tone,
        camera=camera,
        watch_origin=origin,
        watch_axes=axes,
        light=_choice(rng, LIGHT_CONDITIONS),
        light_elevation_deg=float(rng.uniform(30, 80)),
        light_azimuth_deg=float(rng.uniform(0, 360)),
        light_intensity=float(rng.uniform(1.0, 1.6)),
        fill_intensity=float(rng.uniform(0.25, 0.45)),
        surface=surface,
        surface_colour=colours[surface],
        dial_time=(seconds // 3600 or 12, seconds // 60 % 60, seconds % 60),
        tilt_deg=tilt,
        roll_deg=roll,
        distance_mm=distance,
        crown_towards_hand=crown_towards_hand,
        post=Post(
            exposure=float(rng.uniform(0.14, 0.24)),
            blur_px=float(rng.uniform(0.3, 1.0)),
            noise=float(rng.uniform(1.0, 3.5)),
            vignette=float(rng.uniform(0.0, 0.12)),
            jpeg_quality=int(rng.integers(82, 96)),
        ),
        seed=seed,
    )
