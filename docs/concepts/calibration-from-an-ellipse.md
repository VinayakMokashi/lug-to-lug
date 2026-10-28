# Calibration from an ellipse

The idea the whole project rests on: **the watch already on the wrist is a ruler.** Its case is a circle of known diameter. In a photo that circle appears as an ellipse, and the ellipse says how many pixels a millimetre is and how the wrist is tilted towards the camera. From there, anything else on the wrist can be measured, and any other watch drawn at its true size. This guide explains why, with numbers for the capture rig. The code arrives in Phase 2 (steps 2.3 and 2.4).

## A circle seen at an angle

Put a coin flat on a table and look straight down: it's a circle. Tilt your head and it becomes an ellipse. The ellipse's long axis keeps the coin's full width, and its short axis shrinks with the angle. That is all calibration needs:

```
      straight down                    tilted by θ
          ____                           ________
        /      \                       /          \       long axis  = D × s
       |   D    |                     |            |      short axis = D × s × cos θ
        \______/                       \__________/
```

With *D* the case's diameter in millimetres and *s* the scale in pixels per millimetre:

- **Scale:** s = long axis ÷ D.
- **Tilt:** θ = arccos(short axis ÷ long axis).
- **Tilt direction:** the long axis lies along the line the case turns around, so the short axis points the way it tilts.

These are the *weak-perspective* formulas, exact for a camera far away compared with the watch's size. At 30 cm from a 40 mm case they are close, but not exact. The calibration uses the exact version below.

## The numbers for the rig

The Pixel 9a's main camera has a focal length of about 2831 pixels (4.53 mm on 1.6 µm pixels). An object of size *D* at distance *Z* appears f × D ÷ Z pixels across.

| Distance | 40 mm case appears | Scale |
|---|---|---|
| 25 cm | 453 px | 11.3 px/mm |
| 30 cm | 378 px | 9.4 px/mm |
| 40 cm | 283 px | 7.1 px/mm |

| Tilt (capture block) | Short ÷ long axis | Short axis at 30 cm |
|---|---|---|
| 0° (T00) | 1.000 | 378 px |
| 20° (T20) | 0.940 | 355 px |
| 40° (T40) | 0.766 | 289 px |

At 9.4 px/mm, one pixel of error on the diameter is about 0.1 mm, a 0.26% error in scale. The catalogue's own uncertainty is usually larger: a published "40 mm" means 39.5 to 40.5 mm, a 1.25% uncertainty in scale before a single pixel is measured.

## The exact version: a cone through the camera

Perspective changes two things. The ellipse's centre is no longer exactly the image of the circle's centre, and the ellipse's shape depends on where it sits in the frame, not only on the tilt. The exact relation comes from a cone:

1. The ellipse in the image is a **conic**: the points x where xᵀ C x = 0, with C a 3 × 3 symmetric matrix found by fitting the outline's points.
2. Rays from the camera through every point of that ellipse form a **cone**. With the camera's intrinsic matrix K, its matrix is Q = Kᵀ C K.
3. The case's circle is where a **plane cuts that cone** in a circle of the known radius. Diagonalising Q gives the plane's normal and the circle's centre, in closed form.

The solution comes in two mirror-image pairs: the plane can tilt one way or the other with the same ellipse. The wrist picks one: the dial faces away from the arm and towards the camera, and the visible side wall of the case shows which side is nearer. The closed form is classical computer vision (Shiu and Ahmad 1989; Kanatani and Liu 1993). Step 2.3 implements it and tests it against the synthetic data, where the true circle and pose are in every sample's labels.

## The thickness correction

The circle used is the case's top edge, but the wrist is lower. Scale is f ÷ depth, so the wrist, about one case thickness farther from the camera, appears smaller. With the case top 12 mm above the skin at 30 cm, the skin's scale is 300 ÷ 312 = 96.2% of the case top's. Measuring a 60 mm wrist with the case's scale would give 62.4 mm, an error of 2.4 mm from geometry alone. So every measurement is taken at its own depth: the case top for the watch, the case back (the skin's height) for the wrist and the strap. The catalogue's thickness provides the difference.

## How sure is the scale? The ± in every render

A render's ± millimetres combines two sources:

- **The outline:** the points on the case's edge carry pixel noise. Re-fitting the ellipse many times with the points jittered by that noise (Monte Carlo) gives the spread of the scale.
- **The catalogue:** the diameter's tolerance (± 0.5 mm, ± 0.25 mm or ± 0.1 mm, from how precisely it was published), sampled in the same runs.

The spread of the resulting sizes is the stated interval. A stated interval is only worth something if it holds, so step 2.4 checks **coverage**: on the dev photos, does the true size fall inside the 95% interval about 95% of the time? If it falls inside less often, the intervals are too narrow and get widened, until the number printed on a render is one people can rely on.

## When it can't be trusted

The case's edge is hard to find when a domed crystal or a wide bezel hides it, when the case isn't round, when a strap or a sleeve covers part of it, and in strong glare. For non-round cases the same idea applies with the superellipse outline instead of a circle, since its width and length are known. When the outline can't be found or trusted, the app says so and offers the fallbacks (a coin or a payment card of known size) instead of guessing (step 2.6).

## Where it lives

| What | Where |
|---|---|
| The camera model and ellipse fit | `packages/core/src/lugtolug_core/geometry.py` |
| Calibration from the cone, the thickness correction, the uncertainty | `packages/core` (Phase 2, steps 2.3 and 2.4) |
| Synthetic poses to test it against | Every synthetic sample's labels ([synthetic data](synthetic-data.md)) |

**References**

- Y. C. Shiu and S. Ahmad, "3D location of circular and spherical features by monocular model-based vision", *IEEE International Conference on Systems, Man and Cybernetics*, 1989.
- K. Kanatani and W. Liu, "3D interpretation of conics and orthogonality", *CVGIP: Image Understanding* 58(3), 1993.
- A. Fitzgibbon, M. Pilu and R. Fisher, "Direct least square fitting of ellipses", *IEEE TPAMI* 21(5), 1999; R. Halíř and J. Flusser, "Numerically stable direct least squares fitting of ellipses", *WSCG* 1998.
