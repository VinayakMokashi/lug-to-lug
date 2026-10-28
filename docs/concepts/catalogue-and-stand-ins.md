# Catalogue and stand-ins

To show a watch on a wrist at its true size, Lug to Lug has to draw a watch the visitor doesn't have. It draws it from numbers: diameter, lug-to-lug, thickness, the width of the dial opening. This guide explains where those numbers come from, how the project keeps them honest, and how they become a drawing. The decision behind it is [ADR-0009](../decisions/0009-catalogue-and-stand-in-specification.md).

## Two kinds of truth

| | Measured | Published |
|---|---|---|
| Where from | Digital calipers on the reference watches, three separate rounds | A manufacturer's page, sometimes a review |
| Precision | Hundredths of a millimetre; the range of the three readings is the measuring error | Usually whole or half millimetres |
| Gaps | None: every field is measured | Lug-to-lug and thickness are often missing |
| File | `data/catalogue/reference.csv` | `data/catalogue/published.csv` |

Both matter. The reference watches are the ground truth for the benchmark. The published catalogue is what a visitor actually chooses from.

## Facts versus a recipe

The project keeps two descriptions of a watch, on purpose.

- A **catalogue entry** holds facts, each with its source. Anything no source gives stays `null`: unknown.
- A **stand-in specification** is a complete recipe for drawing: every length, the outline, the colours. A renderer can't draw "unknown", so the recipe has to fill the gaps.

Keeping them apart means a guess can never pass for a fact. The catalogue says what is known. The stand-in says what was drawn, and lists every dimension it had to assume.

## Every value has a source

Each row of `published.csv` names a main source, usually the manufacturer's page. The brand, model, reference number and every value come from it, unless `field-sources.csv` gives that one value a different source (say, a review that measured lug-to-lug).

When the API serves an entry, every value carries its citation:

```json
"lug_to_lug_mm": { "value_mm": 47.5, "tolerance_mm": 0.25, "source": "S0002" }
```

**Tolerance from precision.** A source that writes "40 mm" is rounding to the millimetre, so the true value can be anywhere from 39.5 to 40.5. The rule:

| Written as | Tolerance |
|---|---|
| `40` (whole millimetres) | ±0.5 mm |
| `40.5` (halves) | ±0.25 mm |
| `39.7`, `11.95` (finer) | ±0.1 mm, the floor for the variation between two watches of the same reference |

That tolerance is part of the ± printed on a render: a try-on can't be more certain than the size it was given. The reference watches will test the rule, because a measured watch that is also a published reference shows how far the published number really is.

## Filling the gaps honestly

`build_spec()` turns what is known into a complete stand-in. Each unknown dimension is filled from typical proportions of current watches, and its path goes into `assumed`:

| Unknown | Filled with |
|---|---|
| Thickness | 0.3 × diameter |
| Lug-to-lug | 1.2 × diameter, and at least 1.1 × the case length |
| Lug width | Half the diameter, to the nearest even millimetre |
| Dial opening | 0.74 to 0.88 × diameter, depending on the bezel (a dive bezel leaves the least dial showing) |
| Crown | Diameter 0.15 × the case diameter, standing out 2.5 mm, at 3 o'clock |

A 40 mm diver with only its diameter published comes out with a 48 mm lug-to-lug, and the stand-in says so:

```json
"assumed": ["case.thickness_mm", "bezel.outer_mm", "dial.opening_mm", "lugs.lug_to_lug_mm", ...]
```

A fit report that depends on lug-to-lug can then say "assumed" instead of presenting 48 mm as a fact. Colours, finish and markings are always approximate in a stand-in, so they are never listed.

`check_spec()` holds the rules a schema can't express: the dial opening is smaller than the case, lug-to-lug is at least the case length, a round case is as long as it is wide, and so on. Every rule has a test that breaks it on purpose.

## One outline for every shape

Round, cushion, tonneau and square cases are all drawn from one curve, the **superellipse**:

```
|x / a|^n + |y / b|^n = 1        a = half the width, b = half the length
```

- n = 2 gives a circle (or an ellipse, when a ≠ b);
- n ≈ 4 gives a cushion;
- n ≈ 10 gives a square with small rounded corners;
- a **taper** narrows the ends towards 12 and 6 o'clock, which turns a rounded rectangle into a tonneau.

One curve means one drawing path in every renderer, and it belongs to the family of star-convex shapes that the case-outline model in Phase 2 is built to find. No source publishes these parameters, so for non-round cases they are always assumed.

## One schema, two languages

The stand-in is drawn by Python (the photo renderer, the synthetic data) and by TypeScript (live AR in the browser). Both must agree on every field, so the contract is written once:

```
data/schemas/*.schema.json ──► scripts/contracts.py ──────► lugtolug_core/contracts/*.py   (Pydantic)
       (the source)       └──► apps/web/scripts/contracts.mjs ──► src/lib/contracts/*.ts   (TypeScript)
                                         CI regenerates both and fails on any difference
```

Three details make the generated code trustworthy:

- **Strict types.** By default Pydantic turns `"40"` into 40 and `"yes"` into `true`, which JSON Schema rejects. The generated models use strict types, so Python accepts exactly what the schema accepts. A test feeds the same broken examples to both and expects both to refuse.
- **Bundling.** Each schema is generated together with only the shared definitions it uses, so no module carries types it doesn't need.
- **Never edited by hand.** A generated file says so in its first line. CI regenerates both languages and compares them with the committed files.

## Where it lives

| What | Where |
|---|---|
| Schemas | [`data/schemas/`](../../data/schemas/) |
| Catalogue files and their rules | [`data/catalogue/`](../../data/catalogue/README.md) |
| Generated Python models | `packages/core/src/lugtolug_core/contracts/` |
| Defaults and rules | `packages/core/src/lugtolug_core/standin.py` |
| Loading and checking the catalogue | `packages/core/src/lugtolug_core/catalogue.py` |
| Generated TypeScript types | `apps/web/src/lib/contracts/` |
