"""The camera model and the ellipse fit."""

from __future__ import annotations

import math

import numpy as np
import pytest

from lugtolug_core.geometry import Camera, Ellipse, FloatArray, fit_ellipse


def test_the_pixel_9a_main_camera() -> None:
    camera = Camera.pixel_9a()
    assert (camera.width, camera.height) == (4000, 3000)
    assert camera.fx == pytest.approx(2831.25)
    horizontal_fov = 2 * math.degrees(math.atan(2000 / camera.fx))
    assert horizontal_fov == pytest.approx(70.5, abs=0.1)
    small = Camera.pixel_9a(1000)
    assert (small.width, small.height) == (1000, 750)
    assert small.fx == pytest.approx(707.8125)


def test_a_camera_looking_straight_down() -> None:
    camera = Camera.pixel_9a(1000).looking_at(
        eye=np.array([0.0, 0.0, 300.0]), target=np.zeros(3), up=np.array([0.0, 1.0, 0.0])
    )
    assert np.allclose(camera.centre, [0, 0, 300])
    centre, right, up = camera.project(np.array([[0.0, 0, 0], [10, 0, 0], [0, 10, 0]]))
    assert np.allclose(centre, [500, 375])
    assert right[0] > centre[0]  # +x is right
    assert right[1] == pytest.approx(centre[1])
    assert up[1] < centre[1]  # +y is up
    assert up[0] == pytest.approx(centre[0])
    # 10 mm at 300 mm is f * 10 / 300 pixels.
    assert right[0] - centre[0] == pytest.approx(camera.fx * 10 / 300)


def test_rays_pass_through_the_points_they_came_from() -> None:
    camera = Camera.pixel_9a(400).looking_at(
        eye=np.array([40.0, -120.0, 260.0]), target=np.array([0.0, 0, 20]), up=np.array([0, 1.0, 0])
    )
    points = np.array([[0.0, 0, 20], [15, -8, 31], [-22, 12, 5]])
    rays = camera.rays(camera.project(points))
    towards = points - camera.centre
    towards /= np.linalg.norm(towards, axis=1, keepdims=True)
    assert np.allclose(rays, towards)
    every = camera.rays()
    assert every.shape == (400 * 300, 3)
    assert np.allclose(np.linalg.norm(every, axis=1), 1)


@pytest.mark.parametrize("angle", [0.0, 0.4, 1.2, 2.9])
def test_an_exact_ellipse_is_recovered(angle: float) -> None:
    truth = Ellipse(cx=2103.5, cy=1488.25, a=212.0, b=140.0, angle=angle)
    fitted = fit_ellipse(truth.points(36))
    assert fitted.cx == pytest.approx(truth.cx, abs=1e-6)
    assert fitted.cy == pytest.approx(truth.cy, abs=1e-6)
    assert fitted.a == pytest.approx(truth.a, abs=1e-6)
    assert fitted.b == pytest.approx(truth.b, abs=1e-6)
    assert fitted.angle == pytest.approx(angle, abs=1e-9)


def test_noise_averages_out() -> None:
    truth = Ellipse(cx=1000, cy=800, a=200, b=190, angle=0.3)
    rng = np.random.default_rng(7)
    noisy = truth.points(60) + rng.normal(0, 0.5, size=(60, 2))
    fitted = fit_ellipse(noisy)
    assert fitted.a == pytest.approx(200, abs=0.5)
    assert fitted.b == pytest.approx(190, abs=0.5)
    assert math.hypot(fitted.cx - 1000, fitted.cy - 800) < 0.3


def test_a_circle_has_equal_axes() -> None:
    fitted = fit_ellipse(Ellipse(50, 60, 30, 30, 0).points(20))
    assert fitted.a == pytest.approx(30)
    assert fitted.b == pytest.approx(30)


@pytest.mark.parametrize(
    ("points", "message"),
    [
        (np.zeros((4, 2)), "at least five"),
        (np.ones((6, 2)), "all the same"),
        (np.column_stack([np.arange(8.0), 2 * np.arange(8.0)]), "don't determine an ellipse"),
    ],
)
def test_points_that_are_no_ellipse(points: FloatArray, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        fit_ellipse(points)


def test_a_hyperbola_is_not_an_ellipse() -> None:
    with pytest.raises(ValueError, match="not an ellipse"):
        Ellipse.from_conic(np.array([1.0, 0, -1, 0, 0, -1]))
