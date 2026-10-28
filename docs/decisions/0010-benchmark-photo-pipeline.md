# ADR-0010: Benchmark photo pipeline

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

The capture sessions ([protocol](../data/capture-protocol.md)) produce folders of phone photos named by the time they were taken, plus a session plan saying what each placement was. Before any of it can be labelled or measured, four things have to be settled:

- **Pairing.** The plan is the only record of which watch each photo shows, and pairing photos with it in order breaks silently when one placement gets an extra photo and the next one too few.
- **Metadata.** Phone photos carry capture times, sometimes a location, a compass heading and an encrypted maker note, none of which may reach a published file. Removing them must not change the pixels the benchmark measures.
- **Storage.** The originals are backed up through a file sync of the private store. Derived copies roughly double the space and can always be rebuilt.
- **Hashes.** The test split will be frozen as a list of file hashes (step 1.6), so the files it names must never change once written.

## Decision

1. **A plan-driven ingest that never guesses** (`uv run poe ingest <session>`). Photos are paired with the plan only when three checks agree:
   - **count:** one slate plus each placement's `shots`;
   - **timing:** photos less than 8 seconds apart form a group, and the groups must match the placements one for one;
   - **camera:** one phone, lens, zoom and image size, plain photo mode, a focus distance outside macro range, the same way up as the photo before, and the planned date.

   Otherwise nothing is written, and the report names the first point of disagreement. The fix is a correction to the plan. `--trust-order` pairs in order when only the timing disagrees, and the report records it.
2. **Every set is a session.** One folder holds one block, starting with one slate photo. The handheld photos and the two passes of product photos are sessions too, so one tool and one rule cover every photo.
3. **Benchmark names say what a photo shows:** `P01_S03_T20-DAY_07_W12_1` is person, session, block, placement, watch and shot (product photos have no person). The placement number keeps a re-seat check's four placements of the same watch apart.
4. **Metadata is removed at the level of the file's segments.**
   - The compressed image data is copied byte for byte, and only a short list of EXIF tags is kept: camera, lens, focal length, digital zoom, focus distance, aperture, exposure and ISO.
   - XMP, comments, the gain map and everything after the image are dropped. The colour profile is kept.
   - Every copy is decoded and compared with its original before anything is written.
5. **Three storage tiers:**

   | Tier | Holds | Backed up | Public |
   |---|---|---|---|
   | Private store | Originals; private manifests with the original names and capture times | Yes | No |
   | Work folder | The renamed, stripped copies | No: rebuildable | No |
   | Repository | Public manifests: names, what each photo shows, SHA-256, size, lens, exposure | Git | Yes |

   The work folder holds personal data even though it is rebuildable, so a withdrawal deletes from it too.
6. **Turned photos are recorded, never corrected silently.** A phone decides which way is up from gravity, which is ambiguous when it points straight down, and stores the result in the pixels. A 90° turn changes the image size; a 180° turn is found by comparing each photo with the one before. A person checks a flagged photo, and `--turned` records the turn in the manifest (`turned_deg`).
7. **Labels live in the stored pixel frame** ([`annotation.schema.json`](../../data/schemas/annotation.schema.json)), so they never depend on a viewer's rotation. Each label records its provenance: how it was made, by whom, the proposing model and the tool. Only drawn, accepted or corrected labels count as checked by a person.
8. **Outputs are idempotent.** The same folder and plan give byte-identical files, and a re-ingest that would change them is refused unless `--replace` is given.
9. **The phone's settings are verified from its own files.** `uv run poe phone-check <folder>` reads a short test series and reports what documentation couldn't confirm: whether the focus and exposure lock held, whether a gain map is still written, the colour profile, and whether the phone stayed the same way up.

## Consequences

- A labelling mistake costs a one-cell correction to the plan, made before any photo is renamed, instead of mislabelled data found weeks later.
- Every block needs its slate photo, and the 8-second gap assumes the two photos of a placement are taken promptly. `--gap` changes it for a slower rhythm.
- The withdrawal procedure covers four places: the private store, its backup (bin included), the work folder and any published release.
- The public manifests let anyone check that a published result used exactly the files it claims, even though the photos themselves stay private unless a person opted in.

## Alternatives considered

- **Pairing on the count alone:** two errors that cancel out go unnoticed.
- **Reading the slates with a vision model to align:** a slate marks only the start of a block, while timing marks every placement.
- **Re-encoding to remove metadata:** every pixel changes, and the copy is no longer the photo that was taken.
- **An external metadata tool:** another binary to install and pin, when keeping a short list of tags is a few lines of tested code.
- **Derived copies inside the backed-up store:** it doubles the backup for files that can be rebuilt.
- **No copies, stripping on the fly in every tool:** each tool would repeat the stripping and naming, and a frozen hash needs fixed files.
- **Rotating turned photos:** lossy, or lossless only in whole JPEG blocks; recording the turn keeps the pixels as taken.
