# Data card: synthetic data v0

| | |
|---|---|
| **What** | Rendered photos of parametric watches on forearms, with exact labels |
| **Use** | Training only: pre-training and augmenting the case, dial and wrist models (Phase 2). Never evaluation |
| **Made by** | `lugtolug-ml` 0.1.0, `uv run poe synth --count 1000 --seed 0 --width 1024` |
| **Where** | The work folder next to the repository (`work/synthetic/v0`). Not committed and not published: rebuildable from the command |
| **People** | None. No photo of a person went into it, and nothing in it depicts a real person |
| **How it works** | [Concept guide](../concepts/synthetic-data.md) |

## Contents

Each sample is a JPEG (1024 × 768), a PNG class mask and a JSON label file ([format](../../ml/src/lugtolug_ml/synthetic/labels.py)), plus one row in `manifest.csv`.

| Mask value | Class |
|---|---|
| 0 | Background: the surface the arm lies on |
| 1 | Skin |
| 2 | Strap |
| 3 | Lugs and crown |
| 4 | Case and bezel |
| 5 | Dial |

The labels also carry the projected outlines of the case top and back, the bezel and the dial opening; the camera and watch poses; pixels per millimetre at the case top; the reference circle and its image for round cases; and the wrist's width, thickness and circumference.

**Statistics** (counts per skin tone, light, surface, tilt, case shape, and so on) are measured from the finished run and added here then.

## How it is sampled

Every sample is drawn from a random generator seeded with `[0, i]`.

| Factor | Distribution |
|---|---|
| Skin tone | Monk Skin Tone 1 to 10, uniform. Swatch colours from the Monk Skin Tone Scale by Ellis Monk, CC BY 4.0 ([skintone.google](https://skintone.google)) |
| Wrist | Width 48 to 72 mm, thickness 34 to 50 mm, hand breadth 70 to 95 mm |
| Case shape | Round 70%, cushion 10%, square 10%, tonneau 5%, other 5% |
| Case size | 30 to 46 mm (square cases 26 to 33 mm, length up to 1.35 × width); thickness 7 to 16 mm |
| Bezel | Rotating with insert 35%, smooth 30%, none 20%, fluted 10%, other 5% |
| Material | Steel 60%, titanium, gold, resin, ceramic, bronze |
| Strap | Bracelet 40%, leather 30%, rubber 20%, fabric 10% |
| Placement | On top of the wrist, rolled about N(0°, 4°) around the arm and turned N(0°, 4°); crown towards the hand 80% of the time |
| Camera | Pixel 9a main camera; 25 to 40 cm away; tilted 0° to 45° around the arm, either side; turned in the image ±20°, and half the time the other way round |
| Light | Daylight, warm lamps or a mix, one third each; key light 30° to 80° up, any direction |
| Surface | Grey card 60%, desk 25%, fabric 15% |
| Camera effects | Exposure on the surface, vignetting up to 12%, blur 0.3 to 1.0 px, noise 1 to 3.5 grey levels, JPEG quality 82 to 95 |

## Label accuracy

The outlines, poses and numbers are computed from the scene's geometry. The class mask depends on step sizes:

- **forearm and strap:** stepped at 1 mm along each ray and bisected 12 times. A 1024-px render differs from a 0.25 mm reference in about 60 of its 786,432 pixels, all on the strap's edges (measured on one sample, 2026-10-28);
- **watch:** sliced every 0.35 mm, which moves a tilted wall's edge by less than a pixel.

The tests check that masks and outlines agree. Straight down, a round case's image is a circle whose radius matches the labelled scale to within 3%; tilted by 30°, it is squeezed by the cosine.

## Limitations

What separates these images from real photos:

- **Hands** are smooth paddles with no fingers or knuckles; **skin** has no hair, veins, creases or freckles, only smooth colour variation.
- **Light** comes from one key light, a fill and a simple sky. There is no light bouncing between surfaces, and shadows are softened by a blur rather than computed from the light's size.
- **Dials** carry hour markers and hands but no text, numerals, logos, sub-dials or date windows. Crystals are flat.
- **Straps** are shells around the wrist with a simple ramp at the lugs: no buckle, no keepers, no gap between strap and skin.
- **Placement:** the watch always sits on top of the wrist. Nothing covers it (no sleeves, no other hand), and nothing else is in the frame.
- **Camera:** an ideal pinhole with no lens distortion, until the phone is calibrated.

Because of these gaps, the data trains models but never measures them. Phase 2 measures the gap directly: models trained on synthetic data alone, and on synthetic plus real training photos, are compared on the real dev split.

## Out of scope

- **Evaluation of any kind:** every reported number comes from real, consented photos.
- **Representing real people:** skin tones are swatch colours, sampled evenly to train evenly. They say nothing about anyone's appearance.
