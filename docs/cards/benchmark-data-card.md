# Data card: Lug to Lug wrist benchmark

**Status: skeleton.** Collection has not started. Every number on this card is filled in from the data itself when the dataset is frozen (Phase 1 exit), and only then.

| | |
|---|---|
| Version | not yet frozen |
| Collected | not yet |
| Collection protocol | [capture-protocol.md](../data/capture-protocol.md) |
| Consent | [consent-form.md](../data/consent-form.md), signed by every participant ([ADR-0006](../decisions/0006-data-consent-and-privacy.md)) |
| Licence of the published parts | decided at release |

## Purpose

Ground truth for measuring how accurately Lug to Lug sizes a watch on a wrist:

- **swap tests:** pairs of photos of the same wrist and camera pose with two different watches;
- **calibration:** whether the stated ± mm contains the truth at its nominal rate;
- **wrist measurement:** circumference and width against tape and calipers;
- **identification** of the worn watch.

### Out of scope

Identifying people, or estimating anything about a person beyond wrist and hand size. The data is not suitable for training models to recognise individuals, and must not be used for that.

## Composition

| | Count |
|---|---|
| Participants | not yet collected (planned: four, P01–P04) |
| Reference watches | not yet collected (planned: 35 to start, W01–W35) |
| Sessions and blocks | not yet collected |
| Photos | not yet collected |
| Same-pose swap pairs | not yet collected |
| Re-seat pairs (the same watch placed twice) | not yet collected |

**Per photo:** participant ID, session, block (camera tilt and light), watch ID, shot number, focal length and image size.

**Per participant:** wrist circumference, wrist width and hand breadth (three readings each, per session), the arm photographed, and a Monk Skin Tone group.

**Per watch:** case diameter, bezel diameter, dial opening, lug-to-lug, thickness and lug width (three caliper readings each), case shape, bezel type, colours and strap type. Who owns a watch is never recorded.

### Slices

Results are reported by camera tilt, light, skin-tone group (Monk 1–3, 4–6, 7–10), wrist size and case shape. Slice sizes are reported too, and thin slices are marked as thin.

## Collection

- One phone (a Google Pixel 9a, main camera only), on a rigid overhead mount about 30 cm above a matte mid-grey backdrop, plus a smaller set on everyday surfaces and handheld photos.
- Three camera tilts (0°, about 20° and about 40°) and three lighting conditions (daylight, warm indoor, mixed).
- Calipers with 0.01 mm resolution and a soft tape. Measuring error comes from three separate rounds of readings.

## Annotations

Case outline points, wrist edges and watch identity. Each label records its provenance: drawn by a person, or proposed by a model and corrected by a person. Counts by provenance are reported here at release.

## Splits

Grouped by watch and by person, so no test watch and no test wrist is seen in training or tuning. The test manifest (file hashes) is committed before any tuning. Swap pairs never cross splits.

## Privacy

- Participants appear only as pseudonymous IDs; names exist only on the signed consent forms, kept privately.
- Raw photos are kept privately on the project owner's computer, with a private Google Drive backup, outside the repository. Location data is stripped on ingest.
- Images are published only for participants who opted in, cropped to wrist and watch.
- Withdrawal removes a participant from every later release.

## Known limitations

Filled in at release. Expected ones: few participants, one phone model, one region and its light, and studio conditions over-represented compared with everyday photos.

## Maintenance

Each release is versioned, with a changelog of additions and withdrawals.
