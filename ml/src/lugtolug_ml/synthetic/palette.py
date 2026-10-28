"""Colours, lights and materials for the synthetic renderer.

Shading is done in linear light, so every sRGB colour is converted before use and the
final image is converted back.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from lugtolug_core.geometry import FloatArray

# The ten swatches of the Monk Skin Tone Scale, by Ellis Monk, released under CC BY 4.0
# (https://skintone.google). Every tone is sampled equally often.
MONK_SKIN_TONES = (
    "#f6ede4",
    "#f3e7db",
    "#f7ead0",
    "#eadaba",
    "#d7bd96",
    "#a07e56",
    "#825c43",
    "#604134",
    "#3a312a",
    "#292420",
)


def srgb_to_linear(values: FloatArray) -> FloatArray:
    values = np.asarray(values, float)
    linear: FloatArray = np.where(
        values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4
    )
    return linear


def linear_to_srgb(values: FloatArray) -> FloatArray:
    values = np.clip(np.asarray(values, float), 0, 1)
    encoded: FloatArray = np.where(
        values <= 0.0031308, values * 12.92, 1.055 * values ** (1 / 2.4) - 0.055
    )
    return encoded


def hex_to_linear(colour: str) -> FloatArray:
    rgb = np.array([int(colour[i : i + 2], 16) for i in (1, 3, 5)], float) / 255
    return srgb_to_linear(rgb)


@dataclass(frozen=True)
class Lighting:
    """The key light's and the fill light's colours, in linear RGB."""

    key: tuple[float, float, float]
    fill: tuple[float, float, float]


# DAY: window light; WARM: lamps at about 3000 K; MIX: a warm lamp against window light.
LIGHTS = {
    "DAY": Lighting(key=(1.0, 0.97, 0.93), fill=(0.82, 0.9, 1.0)),
    "WARM": Lighting(key=(1.0, 0.68, 0.38), fill=(0.9, 0.66, 0.45)),
    "MIX": Lighting(key=(1.0, 0.7, 0.42), fill=(0.8, 0.88, 1.0)),
}


@dataclass(frozen=True)
class Material:
    """How a surface reflects light: metals mirror their surroundings, others scatter."""

    metal: bool
    specular: float
    shininess: float


MATERIALS = {
    "skin": Material(metal=False, specular=0.05, shininess=12),
    "matte": Material(metal=False, specular=0.01, shininess=4),
    "wood": Material(metal=False, specular=0.08, shininess=20),
    "fabric": Material(metal=False, specular=0.02, shininess=4),
    "leather": Material(metal=False, specular=0.12, shininess=18),
    "rubber": Material(metal=False, specular=0.05, shininess=8),
    "dial": Material(metal=False, specular=0.18, shininess=40),
    "insert": Material(metal=False, specular=0.35, shininess=60),
    "brushed": Material(metal=True, specular=0.6, shininess=30),
    "polished": Material(metal=True, specular=1.0, shininess=140),
    "ceramic": Material(metal=False, specular=0.6, shininess=120),
    "resin": Material(metal=False, specular=0.08, shininess=10),
}
