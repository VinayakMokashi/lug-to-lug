# ADR-0009: Catalogue and stand-in specification

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

Every try-on draws a watch the visitor doesn't have, from its dimensions alone, and every fit report compares lengths. Three parts of the system need the same description of a watch:

- the 2.5-D renderer (Python, Phase 3);
- the 3-D stand-in for live AR (TypeScript, Phase 5);
- the synthetic data generator (Python, step 1.8).

The dimensions come from two sources of very different quality. Calipers on the reference watches give medians to a hundredth of a millimetre. Published specifications often leave out lug-to-lug and thickness, and round the rest to the millimetre.

[ADR-0004](0004-web-stack.md) decided that shared contracts are written once in JSON Schema, with the Python and TypeScript types generated from them. This record settles how.

## Decision

1. **Three contracts in `data/schemas`**, JSON Schema 2020-12, plus `common.schema.json` for the shared vocabularies:
   - `StandInSpec`: the recipe for drawing a watch;
   - `CatalogueEntry`: one reference's cited facts, in the form the API serves;
   - `ImageAnnotation`: the labels of one benchmark photo, which is also the published annotation format.
2. **The models are generated, never written by hand.**
   - `scripts/contracts.py` runs datamodel-code-generator into `lugtolug_core.contracts`; `apps/web/scripts/contracts.mjs` runs json-schema-to-typescript into `src/lib/contracts`.
   - Each schema is bundled with only the shared definitions it uses, so no module carries unused types.
   - Strict types (no `"40"` for 40, no `"yes"` for true), so Python accepts what the schema accepts.
   - CI regenerates both and fails if the committed files differ.
3. **Rules a schema can't express live in code:** `lugtolug_core.standin.check_spec`. For example, the dial opening is smaller than the case, a round case's length equals its diameter, lug-to-lug is at least the case length, and every assumed field is a real dimension. Each rule has a test that breaks it.
4. **Facts and the drawing recipe are kept apart.**
   - A catalogue entry holds only what a source says. A value no source gives is `null`, never an estimate.
   - A stand-in is always complete. `build_spec` fills each unknown dimension from typical proportions and lists it in `assumed`, so a render that depends on one can say so. Colours, finish and markings are always approximate in a stand-in and are never listed.
5. **One outline model for every case shape:** a superellipse with an exponent (2 for round, about 4 for a cushion, about 10 for a square) and a taper for tonneaus. Sources never publish these parameters, so for non-round cases they are always assumed.
6. **Storage is CSV**, reviewable line by line ([`data/catalogue`](../../data/catalogue/README.md)):
   - `sources.csv` lists every source;
   - `published.csv` has one row per reference and a main source per row;
   - `field-sources.csv` lists only the values cited from elsewhere.

   `lugtolug_core.catalogue` resolves the citations into the JSON form and reports every problem at once. A test loads the committed files, so CI rejects a bad row.
7. **A published length's tolerance comes from its precision:** whole millimetres ±0.5, halves ±0.25, anything finer ±0.1, the floor for the variation between two watches of the same reference. The reference watches will test this rule: where one is also a published reference, its caliper medians show how far published numbers really are.
8. **The reference watches carry no identity in the repository.** `reference.csv` records measurements and appearance under a watch ID. Brands, models and reference numbers stay in the private measuring records.

## Consequences

- Adding a field means one schema change and two regenerations, and every consumer sees it at once.
- Unknown dimensions stay visible all the way to a render's caption.
- Pydantic lists can't enforce JSON Schema's `uniqueItems`; `check_spec` covers the one list where it matters (`assumed`).
- Identification on the reference watches (step 2.5) can't be re-checked from the public repository alone. It is reported in aggregate; the published references can be checked by anyone.

## Alternatives considered

- **Pydantic models as the source, exporting JSON Schema:** one tool fewer, but the TypeScript side would follow the Python code, and the reviewed contract would be an output instead of the source.
- **Hand-written models in both languages, with a test that they agree:** they would drift between the cases the test happens to cover.
- **One JSON file per reference:** nested citations fit naturally, but reviews and bulk additions are harder than with one CSV line per reference.
- **A citation column for every value:** twice the columns, almost all repeating the row's main source.
- **Estimates for unpublished values in the catalogue:** guesses would become indistinguishable from facts.
- **Identities in `reference.csv`:** nothing the public benchmark reports needs them, so the repository leaves them out.
