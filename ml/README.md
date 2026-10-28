# lugtolug-ml

Training data and model code. It runs on the laptop, Kaggle and Modal, never on the serving path:

- **synthetic training data** (Phase 1, step 1.8): `lugtolug_ml.synthetic`;
- case and dial segmentation (StarDist), compared with baselines (Phase 2);
- the image embedder that identifies the worn watch (Phase 2);
- lighting harmonisation (Phase 3);
- the Studio LoRA (Phase 4).

Weights, run outputs and generated data never enter the repository. Model and data cards go in [docs/cards](../docs/cards/).

## Synthetic data v0

```bash
uv run poe synth --count 1000              # into ../work/synthetic/v0, next to the repository
uv run poe synth --count 8 --width 512 --out /tmp/trial
```

A CPU ray caster draws a parametric watch, built from a [stand-in specification](../docs/concepts/catalogue-and-stand-ins.md), on a forearm lying on a grey card, a desk or fabric, through the Pixel 9a's camera model. Every label is computed from the scene, so it is exact: a class per pixel, the projected outlines of the case, bezel and dial opening, the camera and watch poses, the scale at the case top, and the wrist's width and circumference. Sample *i* comes from a generator seeded with `[seed, i]`, so any sample can be re-rendered alone, and an interrupted run is finished by running the same command again.

How it works: [docs/concepts/synthetic-data.md](../docs/concepts/synthetic-data.md). What it contains: [the data card](../docs/cards/synthetic-v0-data-card.md). **Training only, never evaluation.**
