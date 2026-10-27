# Capture protocol

How the ground truth for Lug to Lug is collected: measuring the reference watches, measuring wrists, product photos, and the photo sessions that produce swap-test pairs. It implements step 1.1 of the [build plan](../PLAN.md#phase-1-ground-truth), under the privacy rules of [ADR-0006](../decisions/0006-data-consent-and-privacy.md).

Everything here is written to be repeatable: the same phone, the same distances, the same order, recorded on a sheet as it happens. A mistake that is written down is data; one that isn't is noise.

## 1. Consent comes first

- Nobody is photographed or measured before signing the [consent form](consent-form.md).
- Each person gets a participant ID (P01, P02, …) when they sign. From then on every file, sheet and label uses only the ID.
- The signed form is kept in the private records, never in this repository.
- People who prefer to can cover tattoos, and should take off rings and bracelets on the photographed arm.

## 2. Equipment

| Item | Specification | Notes |
|---|---|---|
| Digital calipers | Stainless steel, 0.01 mm resolution, 150 mm range | Painter's tape on each jaw protects the watches. Zero the calipers **with the tape on**, at the start of every measuring round. |
| Soft tape measure | Millimetre markings | For wrist circumference |
| Overhead phone mount | Rigid, phone 25–40 cm above the wrist, straight down, locking at about 20° and 40° of tilt | A desk-clamp arm or a tripod with a horizontal arm. A gooseneck is not rigid enough. |
| Bluetooth shutter remote | Any | The phone is never touched during a block of photos |
| Backdrop | Matte mid-grey, about A2 | Neutral grey keeps exposure and white balance steady; see PLAN §9 for why not white, black or wood |
| Steel ruler | Millimetre marks | For the product photos |
| Masking tape and a marker | | Arm guide lines on the backdrop, and the slate cards (§7.3) |
| One phone | The same phone for every benchmark session | Its model is recorded on every session sheet |

## 3. Phone settings

Set these once and check them at the start of every session.

| Setting | Value | Why |
|---|---|---|
| Lens | Main camera (1×) only. No 0.5×, 2× or 3×, and no digital zoom. | One lens means one set of optics for the whole benchmark |
| Mode | Plain photo. Not Portrait, Night, Macro or any "AI scene" mode. | These modes blur, sharpen or switch lenses on their own |
| Automatic lens switching | Off. iPhone: turn on Settings → Camera → Macro Control, then tap the flower icon in the viewfinder so macro is off. Android: turn off the scene optimiser. | Close up, some phones silently switch to the ultra-wide lens |
| Format | JPEG (iPhone: Settings → Camera → Formats → Most Compatible) | One format through the whole pipeline |
| Resolution | The phone's default (for example 12 MP), not 48 MP or RAW | Consistent image size |
| Flash, Live Photos, filters, beauty modes | Off | |
| Location tags | Off (iPhone: Settings → Privacy → Location Services → Camera → Never) | Location never needs stripping if it is never recorded |
| Grid and level | On | Helps keep the phone square to the backdrop |
| Focus and exposure | Locked on the watch at the start of each block (press and hold until "AE/AF lock" shows) | The exposure stays the same while watches are swapped |

The image's own metadata keeps the focal length and the image size, which calibration uses. Everything else, including any location, is stripped when photos are copied into the private store (§8).

## 4. Measuring the reference watches (step 1.2)

Each watch gets an ID, W01 to W35 (more may follow), and is measured **three times**. Measure every watch once (round 1), then every watch again (round 2), then a third time (round 3). Measuring the same watch three times in a row would only repeat the first reading from memory; separate rounds measure the real repeatability. Re-zero the calipers at the start of each round.

| Field | How to measure | Unit |
|---|---|---|
| `case_diameter_mm` | Across the case body from 9 to 3 o'clock, at its widest, **without** the crown or crown guards | mm, 2 decimals |
| `bezel_diameter_mm` | Outer diameter of the bezel or top ring, if it is a separate part; leave empty otherwise | mm |
| `dial_opening_mm` | Inner diameter of the bezel: the visible dial and chapter ring, which decide how large the watch looks | mm |
| `lug_to_lug_mm` | From the tip of the upper lugs to the tip of the lower lugs, straight along 12 to 6 o'clock | mm |
| `thickness_mm` | From the case back to the top of the crystal, at the thickest point | mm |
| `lug_width_mm` | Inside distance between the lugs, where the strap fits | mm |

Hold the calipers square to the case, close the jaws gently until they just touch, and read without pressing. Write down what the display shows, even if it looks wrong; a note column is there for anything odd ("bezel insert loose", "domed crystal").

Once per watch, also record (from the watch, not the calipers):

- case shape: round, cushion, tonneau, square, or other;
- bezel type: none, smooth, fluted, rotating with insert, or other;
- case and dial colour, and the strap type: bracelet, leather, rubber, fabric.

**Into the catalogue.** The catalogue value of each dimension is the median of the three readings. Their spread is the measuring error, reported with the catalogue as a repeatability note. The file is `data/catalogue/reference.csv`, which records measurements only, never who owns a watch.

## 5. Measuring wrists

Measure at the start of every session, because wrists change slightly over a day. Measure the arm that wears the watch, and record which one. Three readings of each, taking the tape or calipers away between readings.

| Field | How to measure |
|---|---|
| `circumference_mm` | Soft tape around the wrist where a watch sits: just above the wrist bone, on the forearm side. Snug against the skin, not pulled tight. |
| `wrist_width_mm` | Calipers across the wrist at the same place, from side to side, held level |
| `hand_breadth_mm` | Calipers across the knuckles, from the index finger's knuckle to the little finger's, hand flat |
| `skin_tone_mst` | The person chooses the closest swatch on the [Monk Skin Tone scale](https://skintone.google/the-scale) (1 to 10), matched against the inner forearm in daylight |

Skin tone is recorded only to check that the app works equally well across skin tones, and results are reported in groups (1–3, 4–6, 7–10), never per person.

## 6. Product photos (step 1.3)

One set per watch, used for the real-image catalogue and the product-photo render mode.

1. Lay the watch dial up on the backdrop, with the strap straight along the 12-to-6 line and the crown on the right.
2. If it is easy, set the hands to about 10:10, which keeps them off the dial's centre.
3. Place the steel ruler next to the case, parallel to the 12-to-6 line.
4. Phone on the mount, straight down (0°), about 30 cm above the watch, the case in the centre of the frame.
5. Light: bright, diffuse daylight, no direct sun. Move the light rather than the phone to get rid of reflections on the crystal.
6. Take two photos. Then take one from the side, with the phone level with the case and the crown towards it, which shows the profile.

The ruler lies on the backdrop, lower than the crystal, so it checks the photo's scale only roughly; the measured diameters are the true scale.

## 7. Photo sessions (step 1.4)

### 7.1 Setting up

1. Put the backdrop on a table and the mount behind it, with the phone about **30 cm** above the backdrop.
2. Make an arm guide with masking tape: a line for the forearm to lie along, and a short line where the wrist bone sits. A book against the elbow stops the arm sliding back. The arm returns to the same place after every watch change.
3. The frame covers the forearm from mid-forearm to the knuckles, with the watch near the centre. The whole hand in the frame lets the hand breadth be measured from the photo too.
4. Forearm flat and palm down, hand relaxed with the fingers together.

### 7.2 Blocks

A **block** is one person, one camera tilt and one lighting condition, with the camera untouched from its first photo to its last. Within a block, only the watch changes. That is what makes every pair of photos in a block a swap-test pair.

| Code | Camera tilt | How |
|---|---|---|
| `T00` | Straight down | Mount locked at 0° |
| `T20` | About 20° | The mount tilts the phone sideways, towards the thumb side, rotating around the arm's long axis |
| `T40` | About 40° | As above. The case looks oval, as when someone turns their wrist to look at a watch. |

| Code | Light | When |
|---|---|---|
| `DAY` | Daylight from a window, no direct sun, room lights off | Daytime |
| `WARM` | Warm indoor lamps or ceiling lights only, curtains closed | Evening |
| `MIX` | Window light plus a warm lamp | Late afternoon |

Change the tilt only between blocks, and lock the focus and exposure again at the start of each block.

### 7.3 One block, step by step

1. **Slate.** Photograph a card with the block code written on it, for example `S03 P01 T20 DAY`. It marks where the block begins in the camera roll.
2. **Re-seat check (start).** Put on the first watch of the list, place the arm, take 2 photos. Take the watch off, put it back on, place the arm again, and take 2 more. The two placements of the same watch measure how much the photos differ from re-placing alone; that is the floor under every swap-test error. They also count as the first watch's photos for the block.
3. **The watches.** For each of the other watches on the list, in order:
   - put it on where a watch normally sits (just above the wrist bone), case centred on top of the wrist, strap snug enough that one finger fits under it;
   - place the arm on the guide;
   - take **2 photos** with the remote;
   - write the watch ID and "2" on the session sheet (more photos if one was clearly blurred).
4. **Re-seat check (end).** The first watch again, as in step 2.
5. Measure the wrist again if more than two hours have passed.

A block of the 35 watches is 38 placements (the first watch four times, the others once). It takes about 25 minutes and gives 77 photos, counting the slate.

### 7.4 Who, and how much

| Set | Person | Blocks | About |
|---|---|---|---|
| Studio | P01 | All 9 blocks (3 tilts × 3 lights), every reference watch | 9 × 25 min, in three sittings of three blocks, one per lighting condition |
| Volunteers | P02, P03, P04 | One block each (`T00 DAY`) with 5 watches chosen to span size, shape and dial colour, plus the re-seat check | 15 min each |
| Everyday surfaces | P01 | One mounted block of 10 watches on a desk without the backdrop; then 10 photos taken handheld, as a visitor would, on a desk and on fabric | 30 min |

The handheld photos have no swap pairs; they test calibration and wrist measurement against the tape and calipers, outside studio conditions. More volunteer blocks are added once the first ones work.

### 7.5 The session sheet

One row per placement, filled in during the session (a printed sheet or a spreadsheet on a second device):

| Column | Example |
|---|---|
| `session_id` | `S03` |
| `date` | `2026-11-02` |
| `person_id` | `P01` |
| `block` | `T20-DAY` |
| `seq` | `7` (placement order within the block) |
| `watch_id` | `W12` |
| `shots` | `2` |
| `reseat` | `yes` for the re-seat check placements |
| `notes` | anything that went wrong |

The session header records the phone model, the distance to the backdrop, the surface, the wrist measured and the start and end times.

### 7.6 File names

Photos keep their camera names until they are copied (§8). On ingest they are renamed from the session sheet, in order:

```
P01_S03_T20-DAY_W12_1.jpg
person_session_block_watch_shot
```

The ingest script checks that the number of photos matches the sheet block by block, and uses the slates to realign if a photo is missing or extra. Mismatches are reported, never guessed.

## 8. Storage and privacy

- **Same day:** copy the photos from the phone to the private photo store, then delete them from the phone, its "Recently Deleted" album and any automatic cloud photo backup.
- **The private store** is outside this repository and access-restricted. Raw photos never enter the repository; it holds manifests (file hashes), annotations and numbers only. A pre-commit hook rejects image files under `data/`.
- **On ingest** the location and any other identifying metadata are stripped; the focal length and image size are kept for calibration.
- **Withdrawal:** a person's photos, measurements and labels are deleted from the private store and dropped from every later release (ADR-0006).

## 9. Labels and splits

- Annotations (case outline points, wrist edges, watch identity) record their provenance per label: drawn by a person, or proposed by a model and corrected by a person (step 1.5).
- Splits are grouped by watch and by person, and the test manifest is committed before any tuning (step 1.6). Swap pairs never cross splits.

## 10. Checklist for a session

- [ ] Consent signed for everyone photographed today
- [ ] Phone settings (§3), mount at 30 cm, arm guide in place
- [ ] Session sheet header filled in; wrist measured (§5)
- [ ] For each block: slate, focus and exposure locked, re-seat check, the watches, re-seat check
- [ ] Photos copied to the private store and deleted from the phone the same day
