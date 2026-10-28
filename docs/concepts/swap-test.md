# The swap test

Every virtual try-on claims to show a watch at its true size; Lug to Lug measures whether it does. The measurement is the swap test: render watch B onto a photo of a wrist wearing watch A, then compare with a real photo of the same wrist wearing B. This guide explains how it works and why it is designed the way it is. The harness arrives in step 3.6; the data it needs is collected in Phase 1 ([capture protocol](../data/capture-protocol.md)).

## The problem: the truth is a photo nobody took

To know whether a render of B on someone's wrist is the right size, you'd need a photo of that wrist wearing B, in exactly the same pose, light and camera position. For a visitor's photo that never exists. So the benchmark creates it on purpose.

## Blocks make every pair a natural experiment

A capture **block** is one person, one camera tilt and one light, with the camera untouched from the first photo to the last. Only the watch changes. So for any two watches A and B in a block, the photo of B is the truth for a render of B made from the photo of A.

```
photo of A ──► calibrate from A's case ──► render B at that scale and pose ──┐
                                                                              ├──► compare
photo of B (same block: same wrist, pose, light, camera) ───────────────────┘
```

**How many pairs?** A block of 35 watches gives 35 × 34 = 1190 ordered pairs (A to B and B to A are different tests: each calibrates from its own photo). The nine studio blocks give 10,710 pairs from 684 photos, the three volunteer blocks 20 pairs each, and the desk block 90.

## What is compared

| Metric | How | Why |
|---|---|---|
| **Diameter error** | B's case diameter in the render minus its diameter in the real photo, both in millimetres at the case's plane. Median and 90th percentile | The number a buyer cares about: is it the right size? |
| **Outline overlap** | IoU of the rendered and real case outlines, after centring them | Shape and tilt, separately from small position offsets |
| **Interval coverage** | How often the true size falls inside the render's stated ± | Whether the printed uncertainty can be trusted ([calibration](calibration-from-an-ellipse.md)) |

The real photo's outline comes from a person's label ([labelling](labelling.md)), measured at the same plane as the render.

## The floor: putting the same watch on twice

Even a perfect renderer can't match a real photo exactly, because taking a watch off and putting it back changes how it sits by a fraction of a millimetre. Every block measures that directly: its first watch is placed four times, at the start and at the end, the **re-seat check**. The differences between those photos of the same watch are the **floor**: no swap test can honestly be expected to beat it. Swap errors are reported next to the floor, so a reader can see how much of the error is the method's and how much is just the arm moving.

## Honest statistics

- **Pairs aren't independent.** The 1190 pairs in a block share 35 photos, and each photo appears in 68 pairs. Treating them as independent would give confidence intervals that are far too narrow. The 95% intervals come from a **bootstrap that resamples blocks and watches**, never single pairs.
- **Comparisons are paired.** Two methods, say two case-finding models, are compared on the same pairs, and the test is on the per-pair differences. This removes the variation that both share.
- **Slices are reported, including thin ones:** by tilt, light, skin-tone group (Monk 1 to 3, 4 to 6, 7 to 10), wrist size and case shape. A slice with few people is reported as thin, with its wide interval, rather than left out.

## Keeping the test honest

- **Splits by watch and by person.** No test watch and no test wrist is seen while tuning. A swap pair never crosses splits.
- **A frozen test manifest.** The test photos' SHA-256 hashes are committed before any tuning (step 1.6), so nobody can quietly change what "test" means. The test split is opened only at milestones.
- **Real photos only.** Synthetic images train models but never appear in a reported number ([synthetic data](synthetic-data.md)).

## What it doesn't measure

- **Realism.** A render can be exactly the right size and still look pasted on. Visitors judge that in the "Real or Rendered?" game (Phase 8).
- **Live AR.** The live view has its own scale check against the still photo (Phase 5).
- **Other wrists, phones and rooms.** The benchmark covers the people, phone and rooms in it. The handheld and desk photos, and more volunteers over time, test how far it generalises, and the reports say what it covers.

## Where it lives

| What | Where |
|---|---|
| Block design, re-seat checks and session sheets | [Capture protocol](../data/capture-protocol.md) §7 |
| The harness, metrics and reports | `eval/` (step 3.6) and `docs/eval/swap-tests.md` |
| Splits and the frozen test manifest | Step 1.6, with its decision record |
