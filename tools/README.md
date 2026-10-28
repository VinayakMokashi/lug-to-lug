# lugtolug-tools

Internal tools for building the benchmark from the photo sessions. They read the private store and never write photos into the repository ([ADR-0006](../docs/decisions/0006-data-consent-and-privacy.md)).

| Command | What it does |
|---|---|
| `uv run poe ingest S03` | Matches a session's photos to the session plan, checks count, timing and camera, then writes metadata-stripped copies and the session's manifests. `--dry-run` checks only. |
| `uv run poe reference` | Builds `data/catalogue/reference.csv` from the three measuring rounds: the median of each dimension and its range. |
| `uv run poe label` | Opens the labelling tool in the browser: case outlines, dial openings, wrist edges and the watch, with an outline proposer and a record of how every label was made ([guide](../docs/concepts/labelling.md)). Its Demo source practises on synthetic data. |
| `uv run poe phone-check <folder>` | Checks a series of test photos against the [Pixel 9a settings](../docs/data/pixel-9a-settings.md#the-test-series): lens, zoom, frame, mode, location, gain map, colour profile, and whether the focus and exposure lock held. |

How the ingest works, and why it never guesses: [docs/concepts/photo-ingest.md](../docs/concepts/photo-ingest.md).

## Where the tools read and write

| Place | What | Backed up | In the repository |
|---|---|---|---|
| Private store (`../private`, or `LUGTOLUG_PRIVATE_DIR`) | Photo originals (`raw/sessions/<session>/`), the sheets, private manifests (original names and capture times) | Yes | Never |
| Work folder (`../work`, or `LUGTOLUG_WORK_DIR`) | Metadata-stripped copies (`ingested/<session>/`), rebuilt from the store at any time | No | Never |
| `data/manifests/<session>.csv` | One row per benchmark photo: its name, what it shows, its SHA-256, size, lens and exposure | | Yes |
| `data/catalogue/reference.csv` | The reference watches' medians and ranges | | Yes |

The work folder holds personal data even though it is rebuildable: a withdrawal deletes from it as well as from the store and its backup.
