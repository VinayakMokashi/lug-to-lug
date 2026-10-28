# Catalogue

The dimensions every try-on, fit report and search result is built from. Two kinds of rows, kept apart on purpose:

| File | What | Step |
|---|---|---|
| `reference.csv` | The reference watches, measured with calipers in three rounds: the median of the readings and their range | 1.2 |
| `published.csv` | Popular references with their published dimensions, one row each | 1.7 |
| `sources.csv` | Every source a published value comes from | 1.7 |
| `field-sources.csv` | The published values whose source is not their row's main source | 1.7 |

The format is checked in CI: `lugtolug_core.catalogue` loads every file, and a test fails on any broken rule, listing all of them at once. The JSON form the API serves is [`catalogue-entry.schema.json`](../schemas/catalogue-entry.schema.json); the reasoning is in [ADR-0009](../../docs/decisions/0009-catalogue-and-stand-in-specification.md).

## Rules

- **Every published value has a source.** A row's `source` covers its brand, model, reference and any value without its own line in `field-sources.csv`. A manufacturer's page is preferred; a review or retailer page is used only for values the manufacturer doesn't publish.
- **Unknown stays empty.** Lug-to-lug and thickness are often unpublished. An empty cell means unknown, and nothing downstream may treat it as known. A stand-in drawn without it lists the field as assumed.
- **Numbers as published.** Write a length exactly as the source gives it (`40`, `40.5`, `11.95`). Its tolerance comes from that precision: whole millimetres ±0.5, halves ±0.25, anything finer ±0.1.
- **No bulk collection.** Values are read from individual pages, never scraped in bulk from a site whose terms forbid it. Dimensions are facts; the citation is what makes them checkable.
- **The reference watches carry no identity.** `reference.csv` records measurements and appearance under a watch ID only: no brand, model or reference number, and never who owns a watch.

## Columns

**`published.csv`**: `id` (brand and reference in lower case, joined by hyphens), `brand`, `model`, `reference`, `aliases` (nicknames, separated by `;`), `source`, then the values:

| Column | Meaning | Values |
|---|---|---|
| `case_shape` | Outline from above | `round`, `cushion`, `tonneau`, `square` (covers rectangular), `other` |
| `case_diameter_mm` | 9 to 3 o'clock, without the crown | mm |
| `case_length_mm` | 12 to 6 o'clock without the lugs; non-round cases only | mm |
| `bezel_diameter_mm` | Outer width of a separate bezel or top ring | mm |
| `dial_opening_mm` | Width of the visible dial opening | mm |
| `lug_to_lug_mm` | Tip of the upper lugs to the tip of the lower lugs | mm |
| `thickness_mm` | Case back to the top of the crystal | mm |
| `lug_width_mm` | Inside distance between the lugs | mm |
| `bezel_type` | | `none`, `smooth`, `fluted`, `rotating_insert`, `other` |
| `case_material` | Gold covers yellow, rose and white gold | `steel`, `titanium`, `gold`, `ceramic`, `resin`, `bronze`, `other` |
| `case_colour`, `dial_colour` | As the source names it | `black`, `white`, `silver`, `grey`, `blue`, `green`, `red`, `brown`, `gold`, `champagne`, `cream`, `orange`, `yellow`, `pink`, `purple`, `other` |
| `strap_type` | | `bracelet`, `leather`, `rubber`, `fabric`, `other` |
| `crown_position` | As an hour on the dial | `3` for most watches, `9` for a left-hand crown |

**`sources.csv`**: `id` (`S0001`, …), `kind` (`manufacturer`, `retailer`, `review`, `press`, `other`), `publisher`, `title`, `url`, `accessed` (YYYY-MM-DD), `archived_url` (a web archive copy, or empty).

**`field-sources.csv`**: `entry_id`, `field` (a value column of `published.csv`), `source`.

**`reference.csv`**: `watch_id`, `case_shape`, then each length twice, as the median of the three rounds and its range (`case_diameter_mm`, `case_diameter_range_mm`, …), then `bezel_type`, `case_material`, `case_colour`, `dial_colour`, `strap_type` and `rounds`. It is written by the measurement tooling from the private measuring sheets, never by hand.
