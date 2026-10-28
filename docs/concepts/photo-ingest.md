# Photo ingest

A capture session ends with a folder of photos named by the phone (`PXL_20261102_050021323.jpg`) and a sheet saying what each placement was. The ingest turns the two into benchmark files: every photo renamed to say what it shows, stripped of anything personal in its metadata, and listed in a manifest with its hash. This guide explains how, and why it refuses rather than guesses. The decision behind it is [ADR-0010](../decisions/0010-benchmark-photo-pipeline.md); the commands are in [`tools/`](../../tools/README.md).

## The one place a label can silently go wrong

The session plan says "placement 7 is W12, 2 photos". The camera roll only says in which order the photos were taken. Pairing them in order works until the day one placement gets an extra photo and the next one gets one too few: the total is still right, and every photo after that point carries the wrong watch's name. Nothing downstream could notice. A model would train on wrong labels, and the swap test would compare the wrong watches, all with confident numbers.

So the ingest accepts a pairing only when three independent checks agree.

### 1. Count

One slate, then each placement's `shots`, must add up to the number of photos. This catches a missing or extra photo, but not two errors that cancel out.

### 2. Timing

Photos taken a second or two apart belong to one placement; changing the watch takes twenty seconds or more. Splitting the roll wherever more than 8 seconds pass gives groups, and the group sizes must equal the plan's, one for one:

```
plan:    slate  W01 W01 W02 W03 W01 W01
         1      2   2   2   2   2   2
timing:  1      2   2   3   1   2   2     <- refused: placement 3 has a third photo,
                                             placement 4 is missing one
```

Two errors can't cancel out here, because each group is checked on its own. The report names the first group where plan and timing part ways, with its clock times, which is usually enough to see what happened. The fix is a one-cell correction to the plan (`shots` = 3), never an edit to the photos.

When the plan is right and the timing is misleading (a long pause between the two photos of one placement), `--trust-order` pairs in order anyway, but only if the count is right, and the report records that it was used.

### 3. Camera

Every photo must come from the same phone, lens and zoom, at the same image size, in plain photo mode:

| Check | Catches |
|---|---|
| Model is the benchmark phone | Photos from another device in the folder |
| Same lens and focal length | A switch to the ultra-wide lens |
| `DigitalZoomRatio` at most 1 | 2× zoom, which keeps the focal length and image size the same and shows only in this tag |
| Same width and height | A change of aspect ratio, or the phone deciding it was held the other way |
| Focus distance above 15 cm | The phone far too close (macro range) |
| No `.NIGHT`, `.MP`, `.PORTRAIT`, `.RAW` in the name | Night Sight, motion photos, portrait mode, RAW capture |
| Not turned 180° next to the photo before | The phone storing a photo upside down |
| Capture date matches the plan | Photos from another day copied into the folder |

The last-but-one check deserves a word. A phone decides which way is up from gravity, and pointing straight down, gravity doesn't say. The phone writes the rotation into the pixels themselves, so a 90° change shows up as a different width and height, but a 180° flip keeps the size. Within a block only the watch changes, so consecutive photos are nearly identical. A flipped one differs everywhere, and stops differing when turned back. That is what the check measures, on small grey thumbnails. A flagged photo is looked at by a person; if it really is turned, `--turned NAME=180` records it in the manifest, so later steps can undo it.

## Removing metadata without touching the pixels

A phone photo carries far more than pixels: capture time to the millisecond, sometimes a location, a compass heading, an HDR gain map, and an encrypted maker note. The benchmark keeps only what calibration and the quality checks need: camera model, lens, focal length, zoom, focus distance, aperture, exposure and ISO.

Saving the image again with an image library would do that in one line, and change every pixel, because a JPEG is lossy and re-encoding re-compresses it. Instead the ingest edits the file's **segments**. A JPEG is a sequence of marked blocks, and the compressed image data is one of them:

```
SOI | APP1 EXIF | APP1 XMP | APP2 ICC | APP2 MPF | DQT | SOF | DHT | SOS + scan data | EOI | gain map ...
keep  replace     drop       keep       drop       keep  keep  keep  keep (byte for byte)  keep  drop
```

The scan data is copied byte for byte, so the copy decodes to exactly the same pixels. That isn't left to trust: the ingest decodes every copy and its original and compares them before writing anything.

## What is written, and where

| Output | Where | What |
|---|---|---|
| Benchmark copies | Work folder, `ingested/<session>/` | Renamed, metadata stripped. Rebuildable from the originals, so not backed up |
| Public manifest | `data/manifests/<session>.csv` | One row per photo: its name, person, block, placement, watch, shot, SHA-256, size, lens and exposure |
| Private manifest | Private store, `manifests/<session>.csv` | Original file names and capture times, and which photo was the slate |

A benchmark name says everything about a photo:

```
P01_S03_T20-DAY_07_W12_1
person  session  block (tilt, light)  placement  watch  shot
```

The placement number keeps a re-seat check's four placements of the same watch apart.

**Idempotent.** Ingesting the same folder with the same plan gives byte-identical output, so running it twice is harmless. If the result would differ from an earlier ingest (the plan was corrected, say), it refuses unless `--replace` is given, because the hashes in a manifest will later be frozen into the test split.

## Where it lives

| What | Where |
|---|---|
| Plan reader | `tools/src/lugtolug_tools/plan.py` |
| Matching and checks | `tools/src/lugtolug_tools/ingest.py` |
| Segment-level metadata removal | `tools/src/lugtolug_tools/jpeg.py` |
| Reading the camera's metadata | `tools/src/lugtolug_tools/photos.py` |
| Checking the phone's settings from test shots | `tools/src/lugtolug_tools/phone_check.py` |
| A fake Pixel camera for the tests | `tools/src/lugtolug_tools/testing.py` |
