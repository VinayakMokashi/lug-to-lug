# Labelling

The benchmark measures the app against what a person marked on each photo: where the case's edge is, where the dial opening is, where the wrist's edges are, and which watch it is. This guide explains what is labelled, how the tool works, and why every label records how it was made. The format is [`annotation.schema.json`](../../data/schemas/annotation.schema.json) ([ADR-0010](../decisions/0010-benchmark-photo-pipeline.md)), and the tool is `uv run poe label`.

## What is labelled

| Label | What to mark | Used for |
|---|---|---|
| Case outline | Five or more points (twelve to twenty is better) on the **outer edge of the case's top face**, all the way round. Where the bezel is wider than the case, its outer edge | The reference ellipse that calibrates the photo (step 2.3), and the case-finding models (2.1, 2.2) |
| Dial opening | Points on the edge where the dial meets the bezel or case | A second, concentric ellipse that steadies the calibration |
| Wrist edges | Two or more points along each edge of the forearm, on either side of the watch: the thumb side and the little-finger side | Wrist width and circumference (2.7) |
| Watch | Filled in from the session plan; changed only if the photo shows another watch | Identification (2.5) |
| Flags | Blurred, glare, something covering the watch, the watch out of place, unusable, plus a note | Leaving photos out of the measurements that they would distort |

**The top face's edge, not the silhouette.** When the camera is tilted, the case's side wall shows on one side. Mark the edge where the top face meets that wall, not the wall's lower edge against the wrist. On the far side the wall is hidden, and the top face's edge is the outline itself. This is the circle whose diameter the catalogue gives, so it is the one calibration needs. The synthetic data labels the same edge.

Points are in the photo's own pixels as stored ([the image frame](../../data/schemas/annotation.schema.json)), so a viewer that rotates photos can't shift them.

## How the tool works

```
overview (click: where to zoom)          zoomed view, 1x to 6x (click: add a point)
┌──────────────────────────────┐        ┌─────────────────────┐
│   ┌──┐                       │  ───►  │      · · ·           │
│   │◎ │  forearm              │        │   ·        ·         │
│   └──┘                       │        │  ·    ◎     ·        │
└──────────────────────────────┘        │   ·        ·         │
                                        │      · · ·           │
                                        └─────────────────────┘
```

- **Click the overview** to choose where to zoom. **Click the zoomed view** to add a point to the chosen label. At 4× zoom one screen pixel is a quarter of a photo pixel, so points can land between pixels.
- **Undo** removes the last point and **Clear** empties the label. Once an outline has five points, its fitted ellipse is drawn, which makes a misplaced point easy to see.
- **Propose** (case outline only) takes two clicks: the middle of the case, then a point on its edge. A simple proposer suggests the rest: along rays from the middle it finds the outermost strong change in brightness near the clicked radius, then keeps the points that agree on one ellipse (RANSAC), dropping the lugs and strap. Accept the proposal as it is, or correct it.
- **Save** checks that the photo is still the file that was ingested (its SHA-256), then writes `data/labels/<session>/<photo>.json`. Labels are committed through pull requests like code.

## Every label says how it was made

| Method | Meaning | Checked by a person |
|---|---|---|
| `person_drawn` | A person clicked every point | Yes |
| `model_proposed_person_accepted` | The proposer's points, accepted unchanged | Yes |
| `model_proposed_person_corrected` | The proposer's points, then a person moved, added or removed some | Yes |
| `model_only` | Never checked | No |
| `session_sheet` | Copied from the session plan (the watch) | From the sheet |

Each label also records who checked it (by participant ID), which proposer and version suggested it, the tool and version, and when. This matters because a label a model proposed and nobody checked shares that model's mistakes. Measuring a model against such labels would flatter it, so evaluation only counts labels a person checked. Reporting how many labels were accepted unchanged also shows how good the proposer is, which is a result in itself.

## Practising on synthetic photos

The **Demo** source opens the synthetic data instead of the benchmark, with each image's true outlines drawn in green. Labelling a few demo images shows how close clicked outlines get to the truth, and how well the proposer does. Demo labels are saved in the work folder, never in `data/labels`.

## Where it lives

| What | Where |
|---|---|
| The page | `tools/src/lugtolug_tools/labelling/app.py` |
| Label histories, saving and loading | `tools/src/lugtolug_tools/labelling/store.py` |
| The proposer | `tools/src/lugtolug_tools/labelling/propose.py` |
| Saved labels | `data/labels/<session>/<photo>.json` |
