# ADR-0011: Synthetic data from a hand-written ray caster

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

Phase 2's models must find a watch's case and dial precisely, and real labelled photos will number in the hundreds (step 1.8). Synthetic images can add thousands, evenly spread over skin tones, poses and light, if they come with labels that are exactly right. They must run on a CPU-only laptop, be reproducible bit for bit, and be cheap to change as the stand-in specification ([ADR-0009](0009-catalogue-and-stand-in-specification.md)) grows.

## Decision

1. **A small ray caster in numpy** (`lugtolug_ml.synthetic`). The forearm and strap are implicit surfaces, and the watch is built from its stand-in specification as sliced prisms. Shading is a key light, a fill light and a simple sky for metals.
2. **Labels come from the geometry**, not from the image: class masks, projected outlines, poses, scale, and the wrist's measurements. Their accuracy is measured against finer steps, and the tests check them against the image.
3. **The Pixel 9a's camera model**, from its published focal length and pixel size, so synthetic and real images share a geometry.
4. **Seeded per sample** (`[seed, i]`): any sample can be rebuilt alone, runs can be extended, and an interrupted run is finished by running it again.
5. **Training only, never evaluation**, as the plan requires. The domain gap is measured in Phase 2 on the real dev split.

## Consequences

- No 3-D software to install. Generation runs on any machine with the repository, and the tests run in CI.
- Every image costs about 3 s at 1024 × 768 on one CPU core, so 1000 samples take about an hour on one core, or minutes on several.
- The images look rendered: no fingers, no hair, simple light. If Phase 2 shows the gap hurts, a physically based renderer can replace the shading, keeping the same scenes and labels.

## Alternatives considered

- **Blender, scripted:** better light and materials, but a large install, slow on a CPU without a GPU, and harder to test. A candidate for a later version if the gap demands it.
- **A game engine:** fast and good-looking, but a heavy toolchain for a few shapes, and harder to keep exactly reproducible.
- **Generated images from a diffusion model:** realistic, but sizes and outlines would no longer be exact, which is the whole point.
- **Pasting cut-out watches onto real wrist photos:** realistic skin, but there are too few consented photos, and the watch's pose wouldn't match the wrist's.
