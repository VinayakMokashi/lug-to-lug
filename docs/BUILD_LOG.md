# Build log

One entry per working session, newest first. Each entry records what changed, the commands and results that matter, problems met and the next steps. The plan's steps are referred to by their IDs in [PLAN.md](PLAN.md).

## 2026-10-28 (later): Phase 1 tools: contracts, ingest, Pixel settings, synthetic data, labelling

Everything in Phase 1 that needs no photos, so a photo session becomes benchmark data the day it happens.

**What changed**

- **Data contracts and the catalogue format (#14, [ADR-0009](decisions/0009-catalogue-and-stand-in-specification.md), step 1.7):**
  - JSON Schemas in `data/schemas` for the stand-in specification, the catalogue entry and the image annotation;
  - Pydantic and TypeScript generated from them, with strict types and a CI check;
  - `build_spec` fills unknown dimensions and lists them as assumed, and `check_spec` holds the rules a schema can't express;
  - the catalogue is CSV with a source per value and a tolerance from each number's precision, and `reference.csv` records measurements without identity;
  - the capture protocol now measures non-round cases' length and records the case material.
- **Photo ingest (#15, [ADR-0010](decisions/0010-benchmark-photo-pipeline.md)), in a new `tools/` package:**
  - `poe ingest` pairs photos with the session plan only when count, timing and camera checks agree. It strips metadata at the JPEG segment level, so the pixels are untouched (verified by decoding every copy), and writes public and private manifests;
  - `poe reference` builds the reference-watch table from the three measuring rounds;
  - `poe phone-check` checks the phone's settings from a test series.
- **Pixel 9a settings sheet (#16):** [`docs/data/pixel-9a-settings.md`](data/pixel-9a-settings.md).
  - Each setting is checked against Google's help pages, recent reporting and published Pixel 9a files, with 17 numbered sources.
  - Settings are named rather than given as paths, because Pixel Camera 10.1 moved its menus.
  - A 12-photo test series settles what documentation couldn't: whether the focus lock holds, whether Ultra HDR off removes the gain map, and whether the phone keeps its orientation pointing down.
- **Synthetic data v0 (#17, [ADR-0011](decisions/0011-synthetic-data-renderer.md), step 1.8):**
  - `lugtolug_core.geometry`: the camera model, with the Pixel 9a's intrinsics, and a stable ellipse fit;
  - a new `ml/` package with a numpy ray caster that draws the stand-in watches on forearms;
  - labels computed from the scene;
  - `poe synth`, seeded per sample and resumable;
  - a [concept guide](concepts/synthetic-data.md) and a [data card](cards/synthetic-v0-data-card.md).
- **Labelling tool (#18, step 1.5):** `poe label`.
  - Click-to-zoom with sub-pixel points.
  - A two-click outline proposer.
  - Every label records whether it was drawn, accepted or corrected, by whom and with which tool.
  - A Demo source practises on synthetic data ([guide](concepts/labelling.md)).
- **Concept guides (#19):** [calibration from an ellipse](concepts/calibration-from-an-ellipse.md) and [the swap test](concepts/swap-test.md), with an [index](concepts/README.md).
- **CI:** a separate change filter decides API deploys, so data, tools and ML changes no longer redeploy it, and schema changes run the web checks.

**Results**

| Check | Result |
|---|---|
| `uv run poe check` | ruff, mypy (strict), contracts check, 299 tests |
| `pnpm -C apps/web check` | Clean, with the contracts check |
| Synthetic geometry | Straight down, a round case's image is a circle whose radius matches the labelled scale within 3%; at a 30° tilt it is squeezed by the cosine |
| Synthetic label accuracy | At the 1 mm step, about 60 of 786,432 pixels differ from a 0.25 mm reference, all on strap edges (0.5 mm: 13; 2 mm: 189), on one 1024 × 768 sample |
| Proposer | Median distance to the true edge under 2 px on a synthetic render; nothing proposed on a blank image |
| Ingest | Copies decode to the originals' exact pixels; an extra photo of one watch and a missing photo of the next are refused even though the count is right |
| API image | Builds and answers `/health` locally and on staging; 237 MB, now 330 MB because the core depends on numpy |
| Synthetic v0 run | 443 of 1,000 samples made (1024 × 768, seed 0); finishing it is one resumable command |

**Problems met**

- datamodel-code-generator emitted unused shared definitions as classes and wrapped constrained list items. Each schema is now bundled with only what it uses, and item rules moved into code.
- Pydantic's default (lax) mode accepted `"yes"` as true and `"40"` as a number, which the schema rejects; the generated models use strict types.
- The default lug-to-lug (1.2 × diameter) came out shorter than long cases; it now also follows the case length. A test caught it.
- Adding a workspace member would have broken the API image's locked install, which reads every member's metadata. Found by emulating the build, fixed, and proven by a local Docker build and CI's deploy.
- A CSV row with a decimal comma crashed three readers; each now reports it.
- At steep tilts the strap vanished on the far side; it now rises to the lug tips. Renders took about 9 s; a bounding cylinder cut that to about 3.7 s.
- The proposer "found" a circle on a blank image; a contrast floor fixed it.
- The machine had little free memory, so the synthetic run started on one worker. Two workers later began paging heavily, so the run was stopped cleanly to finish another time. On Windows, stopping a process pool's parent leaves its workers running, so they had to be stopped separately.

**Next**

- Finish the synthetic v0 run (`uv run poe synth --count 1000`) and add its statistics to the data card.
- When the watch list is filled in: check it and pick the volunteers' five watches.
- When the equipment arrives: the phone's test series and `poe phone-check`, then the measuring rounds (`poe reference`) and the photo sessions (`poe ingest`, then labelling).
- The catalogue's published references (1.7), and the splits with the frozen test manifest (1.6).

## 2026-10-28: Dependency updates, a CI fix, and where photos are kept

**What changed**

- **Dependency updates** (Dependabot):
  - merged React 19.3.1, TypeScript 6.0.3 and a wider `uv_build` range (#1, #3, #4);
  - closed the Node 26 updates (#2, #5), because the runtime stays on Node 24 LTS (ADR-0007);
  - Dependabot now ignores the runtime bumps that ADR-0007 pins: Node majors, Python minors and majors, and uv in the API image (#9).
- **CI fix (#10).** On `main`, changes are now detected against the **last green commit** instead of the previous push.
  - Runs on `main` queue one behind the other, and GitHub cancels a waiting run when a newer one arrives. When the updates above were merged in quick succession, the `uv_build` update's run was cancelled, and the next run compared only with its own previous push. So that change was never checked or deployed.
  - The [deploy runbook](runbooks/deploy.md) explains the rule.
- **Storage and phone (#11):**
  - raw photos stay on the project owner's computer, with a private Google Drive backup shared with no one. The consent form says so before anyone signs, and a withdrawal deletes from both;
  - the benchmark phone is a Google Pixel 9a, main camera only.
- **Phase 0 is finished (step 0.4).**
  - The Neon project is in AWS Singapore, Neon's closest region to `asia-south1`, with Postgres 18.6 and pgvector 0.8.6.
  - The Modal workspace's token and the Neon connection string are in Secret Manager. Each is version 1, added by a script that never prints a value.
  - The plan, README and project page now show Phase 1.

**Results**

| Check | Result |
|---|---|
| Local checks after the updates | `uv run poe check` 4 tests pass; `pnpm check` clean with TypeScript 6.0.3 |
| First `main` run with the fix | Compared against `268d768` (the last green commit), ran every job, and deployed both services; both report `53ff6ab` |

**Next**

- The Neon project (pgvector) and the Modal token, which close step 0.4 and Phase 0.
- A Pixel 9a settings sheet before the first photo session; the equipment arrives in about two days.
- Phase 1 build work that needs no photos: the ingest script, the catalogue schema and stand-in specification (1.7), the labelling tool (1.5) and synthetic data v0 (1.8).

## 2026-10-27: Foundations (steps 0.2–0.6) and the capture protocol (step 1.1)

**What changed**

- **Tooling (0.2):**
  - A uv workspace on Python 3.12, with `packages/core` (`lugtolug-core`) and `services/api` (`lugtolug-api`, FastAPI with `GET /health`).
  - Shared tooling at the root: ruff, mypy in strict mode, pytest and poe tasks.
  - `apps/web`: Next.js 16 with TypeScript in strict mode, Tailwind CSS, ESLint and Prettier, built as a standalone server. It has a landing page, a `/status` page that probes the API at request time, and `/health`.
  - pre-commit hooks: gitleaks, and a guard that rejects photos under `data/`.
  - READMEs for the folders still to come, [ADR-0007](decisions/0007-tooling-and-workflow.md) and the [local development runbook](runbooks/local-development.md).
- **CI (0.3):**
  - Python, web and Terraform jobs behind path filters, with uv, pnpm and Next.js caches.
  - The hooks and a full-history secret scan on every run.
  - One aggregate check to require on pull requests.
  - Dependabot for uv, npm, GitHub Actions, Docker and Terraform.
- **Cloud (0.4):**
  - A dedicated Google Cloud project. Its **$10 monthly budget**, measured before credits, was created before any other resource.
  - A versioned Terraform state bucket.
  - `infra/terraform/bootstrap`, which imports the budget and the bucket: APIs, an image registry with cleanup rules, workload identity federation limited to this repository's `main` branch, the deployer and runtime service accounts, and empty secrets.
  - `infra/terraform/envs/staging`, built from a reusable Cloud Run module.
  - [ADR-0008](decisions/0008-infrastructure-and-delivery.md) and the [deploy runbook](runbooks/deploy.md).
- **Walking skeleton (0.5):**
  - Container images for the API and the web app, each with the commit baked in.
  - A reusable deploy workflow: keyless authentication, build and push, `gcloud run services update`, then smoke tests.
  - CI deploys each changed service after its checks pass on `main`, the API before the web app.
- **Project page (0.6):** [vinayakmokashi.github.io/lug-to-lug](https://vinayakmokashi.github.io/lug-to-lug/), published from `docs/site` by an Actions workflow. Its result tiles stay empty until numbers are measured.
- **Phase 1 paperwork (1.1), through pull requests #6 and #7:**
  - the [capture protocol](data/capture-protocol.md);
  - the [consent form](data/consent-form.md);
  - the [benchmark data card skeleton](cards/benchmark-data-card.md).

**Decisions**

- Tooling and workflow ([ADR-0007](decisions/0007-tooling-and-workflow.md)):
  - a uv workspace;
  - pnpm through Corepack;
  - strict types in both languages;
  - pre-commit with a secret scan;
  - Conventional Commits; and pull requests from Phase 1.
- Two Terraform roots, images deployed by CI with Terraform ignoring the image, and keyless deploys from `main` only ([ADR-0008](decisions/0008-infrastructure-and-delivery.md)).
- The capture protocol organises photos in **blocks**: one person, one camera tilt, one light, and a camera that doesn't move. Every pair of photos in a block is a swap-test pair.
  - Each block starts and ends with a **re-seat check**: the same watch placed twice. It measures the error that re-placing the arm alone causes, which is the floor under every swap-test error.
  - Watches are measured in three separate rounds rather than three readings in a row, so the spread reflects real measuring error.

**Results**

| Check | Result |
|---|---|
| `uv run poe check` | ruff and mypy (strict) clean; 4 tests pass |
| `pnpm -C apps/web check` and `pnpm build` | Clean; `/` static, `/health` dynamic, `/status` partially prerendered |
| Full-history secret scan (gitleaks) | No leaks |
| Images | API 237 MB, web 385 MB; both run as non-root users |
| First deploy | Green; both services report the deployed commit, and the web app reaches the API |
| `terraform plan`, both roots, after a CI deploy | No changes |

**Problems met**

- The first CI run failed on Prettier, because a README was written after the formatter ran. Fixed in the next commit.
- Starlette's test client now asks for `httpx2` instead of `httpx`; the dev dependency was switched.
- pnpm 12 writes its lockfile as several YAML documents, so `check-yaml` runs with `--allow-multiple-documents`.
- The pre-commit gitleaks hook scans staged changes only, which CI never has, so CI runs a separate full-history scan with a pinned, checksum-verified gitleaks.
- Terraform could not read the new project until the Resource Manager API was enabled, so it is enabled with `gcloud` before the first plan.
- The project page's hero lost its side padding on phones, and a diagram label was clipped. Both were fixed after checking the page at 390 px.

**Next**

- Finish 0.4: the Neon project (pgvector enabled) and the Modal token, with their values in Secret Manager.
- Dependabot opened five update PRs.
  - Three pass CI and wait for review: React 19.3.1, TypeScript 6 and a wider `uv_build` range.
  - The two that move to Node 26 should be closed while Node 24 is the LTS line, with Dependabot ignore rules for those majors.
- Phase 1, by hand: the watch list, measuring the reference watches, consent, and the photo sessions.
- Phase 1 build work that needs no photos yet:
  - the ingest script for the session plan;
  - the catalogue schema and the stand-in specification (1.7);
  - the labelling tool (1.5);
  - synthetic data v0 (1.8).

## 2026-10-26: Planning (step 0.1)

**What changed**

- Chose the project and its name, and wrote the build plan ([PLAN.md](PLAN.md)) and decision records 0001 to 0006.
- Created the public repository with the licence, README, `.gitignore`, `.gitattributes` and this log.
- Refined the plan:
  - a dedicated Google Cloud project with its own budget alerts;
  - three volunteers, recorded under pseudonymous IDs;
  - equipment specifications;
  - a capture set on everyday surfaces;
  - the custom domain deferred until the personal site exists;
  - an indicative timeline of about six weeks.

**Decisions**

- A true-to-scale try-on calibrated from the worn watch, with sizing measured by swap tests; live AR in the first release ([ADR-0001](decisions/0001-choose-lug-to-lug.md)).
- Documentation kept in the repository ([ADR-0002](decisions/0002-documentation-system.md)).
- Google Cloud with services that scale to zero, and Postgres with pgvector on Neon ([ADR-0003](decisions/0003-deploy-on-google-cloud.md)).
- A Next.js web app and FastAPI services ([ADR-0004](decisions/0004-web-stack.md)).
- GPU work on Modal and Kaggle ([ADR-0005](decisions/0005-gpu-on-modal.md)).
- Consent, storage and retention rules for photos ([ADR-0006](decisions/0006-data-consent-and-privacy.md)).

**Research notes**

- **Existing try-ons:**
  - Brand-facing services: Perfect Corp, GlamAR, Tangiblee, Cappasity, Kivisense.
  - Consumer tools: Photta (renders on generic wrist models), Watch Size Helper (manual placement), Watch Try-On, WatchStrap.
  - They infer the scale or rely on manual placement, and none publishes sizing accuracy. That gap is this project's claim.
- **Google Cloud:** the free trial does not allow GPUs, and upgrading the billing account keeps any remaining credit.
- **Modal:** includes a monthly credit, which should cover Studio serving at demo traffic (re-checked at Phase 4).

**Next**

- Phase 0 from step 0.2: monorepo tooling, CI, the cloud bootstrap (a new Google Cloud project) and the walking skeleton.
- Phase 1 preparation:
  - the equipment is ordered;
  - the consent form (step 1.1) comes before anyone is photographed;
  - the list of reference watches is next.
