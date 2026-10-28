# Build plan

| | |
|---|---|
| **Project** | Lug to Lug |
| **Plan written** | 2026-10-26 |
| **Current phase** | Phase 1, Ground truth (step 1.1 done; Phase 0 finished 2026-10-28) |

This is the living plan. Steps are ticked as they land, every working session gets an entry in [BUILD_LOG.md](BUILD_LOG.md), and changes to the plan are recorded in the [change log](#10-change-log) with the reason. The [status tracker](#11-status-tracker) is at the bottom.

---

## 1. What we are building

A true-to-scale watch try-on that measures instead of guessing. The user photographs their wrist wearing any watch they own. Lug to Lug recognises that watch, looks up its case diameter and uses it as a ruler: a round case of known size appears as an ellipse in the photo, and the ellipse gives both the scale and the tilt of the wrist. It then measures the wrist and renders any other watch on it at its real size, with the sizing error printed on the render.

Around that core it helps people decide:

- a **fit report**: lug overhang, thickness, and how large the watch wears next to watches they own;
- **search by dimensions** in plain English;
- a **swipe deck** that learns size and style preferences;
- an **assistant** that answers sizing questions with sources;
- an **MCP server** that gives other AI applications the same tools;
- a **live AR preview** in the phone browser.

| Example request | What it needs |
|---|---|
| "Will a 41 mm Submariner overhang my wrist?" | Calibration, wrist measurement, fit report |
| "Show the Speedmaster on my wrist next to my Black Bay 58." | Try-on and comparison |
| "Find a 38–40 mm GMT under 12 mm thick that wears like my Black Bay 58." | Search by dimensions, recommender, try-on |
| "Let me see it live." | Live AR |

The core claim is measured, not asserted. A held-out benchmark of real photos (the swap test, §6.3) reports how many millimetres a rendered size is off, with confidence intervals, broken down by pose, lighting, skin tone and wrist size.

## 2. Definition of done

The project is finished when all of these are true:

1. **Live.** A public HTTPS deployment on Google Cloud (Cloud Run, scaled to zero when idle), with per-visitor quotas and budget alerts. It moves to a custom domain, a subdomain of the builder's personal site, once that site exists. The photo try-on works on a phone without an account ([ADR-0003](decisions/0003-deploy-on-google-cloud.md)).
2. **Measured.** Swap-test results for rendered diameter error (mm) and outline overlap, wrist-circumference error, identification accuracy for the worn watch, live-AR scale error, and latency and cost per render. All come with 95% confidence intervals and per-slice results.
3. **Honest per render.** Every render carries its own ± mm, and the app declines when it cannot find or trust the reference.
4. **Three render paths:**
   - a CPU composite, the default;
   - GPU relighting that never alters the dial or the size, optional and capped;
   - live AR rendered on the visitor's device.
5. **Decision help.** A fit report, plain-English search by dimensions, a swipe recommender, an assistant with cited answers, and an MCP server that works from a standard MCP client such as Claude Desktop.
6. **Private by default.** Every person in the benchmark gave written consent. Uploads are processed in memory with location data stripped, saved only on request, deletable, and never trained on without opt-in ([ADR-0006](decisions/0006-data-consent-and-privacy.md)).
7. **Automated.** CI runs lint, types, tests and an eval gate on every pull request. Deploys go through GitHub Actions with Workload Identity Federation, so no service-account keys are stored. Every cloud resource is in Terraform.
8. **Documented.** Build log, decision records, concept guides, runbooks, data and model cards, README and project page are complete.

Accuracy targets are set after the Phase 2 and Phase 3 baselines, not before. A change ships when its paired improvement on the dev split is statistically significant, or when it is neutral on accuracy and better on cost, speed or simplicity.

## 3. Working method

Each phase runs the same loop:

1. **Scope.** Confirm the phase's steps; they often sharpen once the previous phase is done.
2. **Build in small commits.** One purpose per commit, [Conventional Commits](https://www.conventionalcommits.org/) messages, tests passing. Phase 0 bootstraps `main` directly; from Phase 1, work lands through pull requests from `phase-N/<topic>` branches once CI passes.
3. **Ship a vertical slice.** Each phase adds its piece of the web app and deploys it to staging, so something always runs end to end.
4. **Test and measure.** Unit tests for code; eval runs for anything that changes quality. The frozen test split is opened only at milestones.
5. **Document as we go.** A log entry, decision records, and a concept guide for each new component (§4).
6. **Review.** Each phase ends with a demo, the numbers and a list of open questions.
7. **Publish.** The project page is updated at milestones.

## 4. Documentation system

Everything lives in `docs/` next to the code, so it is versioned and reviewed with the code ([ADR-0002](decisions/0002-documentation-system.md)).

| What | Where | When it's written |
|---|---|---|
| Build log | [BUILD_LOG.md](BUILD_LOG.md) | Every working session: what changed, commands, results, problems, next steps |
| Decision records | [decisions/](decisions/README.md) | Every decision that is hard to reverse or easy to forget the reason for |
| Concept guides | `concepts/` | One per component, explaining the idea behind it (for example, how an ellipse gives the wrist's tilt) |
| Evaluation reports | `eval/` | Every measured result, with the command and data version that produced it |
| Data and model cards | `cards/` | When a dataset is frozen or a model is adopted |
| Runbooks | `runbooks/` | Deploy, roll back, rotate secrets, delete a person's data |
| Project page | `site/` (GitHub Pages) | At milestones |

## 5. Architecture

### 5.1 Overview

```
CLIENT      Web app (Next.js): guided capture · try-on viewer · compare slider ·
            swipe deck · assistant · "Real or Rendered?" · live AR on the device
            (MediaPipe hand landmarks + React Three Fiber stand-in)
               │
API         FastAPI on Cloud Run: sessions · quotas · async jobs
               │
MEASURE     photo checks → case outline (StarDist) → ellipse fit → scale and wrist
(CPU)       tilt with ± mm (Monte Carlo) → identify the worn watch (dial text, image
            search, reference numbers) → user confirms → wrist width, flat-top
            width, circumference, hand breadth
               │
RENDER      stand-in from dimensions, or product photo cut out → pose → paint out the
(CPU)       old watch (LaMa) → match lighting + contact shadow → critic
STUDIO      optional relighting with the dial locked (LoRA-tuned diffusion on Modal)
(GPU)
               │
DECIDE      fit report · search by dimensions (text2sql-analyst on Postgres) · sizing
            knowledge with sources · assistant (LangGraph) · swipe recommender
            (Thompson sampling) · MCP server
               │
DATA        Neon Postgres + pgvector · Cloud Storage (artefacts, opt-in saves)
OFFLINE     synthetic data · training on Kaggle and Modal · swap-test benchmark ·
            nightly evaluation
```

### 5.2 Components

| Component | Path | What it does | Runs on |
|---|---|---|---|
| Web app | `apps/web` | Next.js (TypeScript): guided capture, try-on viewer, compare slider, fit report, search, swipe deck, assistant chat, "Real or Rendered?" | Cloud Run |
| Live AR | `apps/web` | MediaPipe hand landmarks and a React Three Fiber stand-in | The visitor's phone |
| API | `services/api` | FastAPI: measure, try-on, fit, search, swipes, assistant (LangGraph), quotas, Studio jobs | Cloud Run |
| MCP server | `services/mcp` | `measure_wrist`, `fit_check`, `try_on`, `search_by_size` over Streamable HTTP with token auth | Cloud Run |
| Core library | `packages/core` | Calibration (ellipse pose, uncertainty), wrist measurement, stand-in specs and the 2.5-D renderer, compositing, fit rules | Inside the API |
| Studio | `services/studio` | GPU relighting with the dial and case face locked | Modal ([ADR-0005](decisions/0005-gpu-on-modal.md)) |
| ML | `ml/` | Training and evaluation code: segmentation, embeddings, harmonisation, the Studio LoRA, synthetic data | Kaggle and Modal GPUs |
| Evaluation | `eval/` | Swap-test harness, metrics, reports, the CI eval gate | CI and laptop |
| Data | `data/` | Catalogue with a source for every dimension, schemas, benchmark manifests (no photos) | Git |
| Infrastructure | `infra/terraform` | Every Google Cloud resource | Terraform |

Shared services:

- **Postgres with pgvector on Neon:** catalogue, image and style embeddings, sessions, swipes, assistant memory.
- **Cloud Storage:** model artefacts, and try-ons a visitor chose to save (deleted automatically after 30 days).
- **Language and vision models:** Groq's free tier first (a vision model for reading dials, an open-weight model for the assistant), with Gemini on Vertex AI as the fallback, behind one small gateway.

### 5.3 Request flows

**Photo try-on (CPU)**

1. Upload; strip EXIF; check blur, exposure and angle.
2. Find the worn watch's case outline, fit an ellipse, recover the scale and the wrist's tilt, and propagate the uncertainty.
3. Identify the worn watch: a vision model reads the dial text, image search runs over catalogue photos, and hybrid search matches reference numbers. The user confirms, or types the diameter; a coin or card is the fallback.
4. Measure the wrist: width at the watch, flat-top width, a circumference estimate, and hand breadth (for live AR).
5. Build the target watch: a stand-in from its dimensions, or a real product photo cut out of its background.
6. Pose it with the calibrated homography, paint out the old watch, match the lighting and add a contact shadow.
7. Run the critic (geometry checks and a vision-model check), then return the render with its ± mm and the fit report.

**Studio (GPU, optional).** The API queues a job; Modal relights the composite with the dial and case face masked; the result lands in Cloud Storage; the web app polls for it.

**Live AR (on the device).** Hand landmarks give the wrist's anchor and orientation. The hand breadth measured in the still photo converts pixels to millimetres, and the 3-D stand-in is drawn at that scale.

**Assistant and MCP.** One LangGraph agent calls the same tools the app uses; the MCP server exposes those tools to other clients.

## 6. Data, evaluation and privacy

### 6.1 Ground truth

| Source | What | Notes |
|---|---|---|
| Reference watches | Watches measured with digital calipers, 35 to start: case diameter (without crown), lug-to-lug, thickness, lug width, plus case shape, bezel, crown position and colours | Three repeat measurements each, to know the measuring error. The data records measurements, never who owns a watch |
| Product photos | Each reference watch shot front-on, on a neutral background, with a ruler in frame | Photos taken for this project; they give the real-image catalogue |
| Wrists | The builder and three volunteers, recorded as P01–P04: circumference by tape at the wrist bone, width by calipers | Consent for each person; everyone wears the same reference watches |
| Capture sessions | Phone on an overhead mount above a matte grey backdrop; poses (top-down, about 20° and 40° tilt); lighting (daylight, warm indoor, mixed); one wrist wearing many watches in the same pose. Plus a smaller set on everyday surfaces (desk, fabric) | Every session yields many same-pose swap pairs; the everyday set tests the system outside studio conditions |
| Annotations | Case outlines, wrist edges, watch identity | Drawn by a person, or proposed by a model and corrected by a person; provenance recorded per label |
| Catalogue | About 300 popular references with published dimensions | Every field cites its source and date; lug-to-lug and thickness marked unknown when unpublished |
| Synthetic | Rendered wrists of varied skin tones and sizes wearing parametric watches, with exact masks, scale and pose | Training only, never evaluation |

### 6.2 Splits

Splits are grouped by watch and by person, so no test watch and no test wrist is ever seen in training or tuning. The test manifest (file hashes) is committed before any model is tuned, and the test split is opened only at milestones. Dev is for tuning and train for fine-tuning; synthetic data only ever goes into train.

### 6.3 Metrics

| Area | Metric |
|---|---|
| Sizing | Swap test: render watch B from the photo of watch A taken in the same pose, then compare with the real photo of B. Reports diameter error in mm (median and p90) and outline IoU after centring |
| Calibration | Coverage of the stated interval: does "± x mm" contain the truth 95% of the time? |
| Wrist | Circumference and width error in mm, against tape and calipers |
| Identification | Top-1 and top-5 accuracy for the worn watch |
| Realism | "Real or Rendered?" fooling rate from visitors' judgments; pairwise preference for Studio over CPU renders |
| Live AR | Scale error against the still-photo measurement; frames per second on reference phones |
| Recommender | Held-out swipe prediction (AUC); swipes until preferences settle |
| Assistant | Faithfulness of answers to their sources, tool-selection accuracy, task success |
| System | Latency per stage (p50, p95); cost per render |

Every rate gets a 95% bootstrap interval, and comparisons use paired tests on the same items. Results are sliced by pose, lighting, skin tone (Monk Skin Tone groups), wrist size and case shape. Thin slices are reported as thin, not hidden.

### 6.4 Privacy and consent

In summary ([ADR-0006](decisions/0006-data-consent-and-privacy.md)):

- Written consent from every person photographed. It states the use (evaluation and training), whether their images may ever be published, and how to withdraw.
- People appear in the data only as pseudonymous IDs (P01, P02, …); names stay in the private consent records.
- Raw photos live outside the repository, which holds manifests, annotations and numbers only. Any image release is an opt-in, person by person.
- Visitor uploads are processed in memory with EXIF stripped. They are saved only on request, deleted automatically after 30 days, deletable on request, and never used for training without opt-in.

### 6.5 Licences and brands

- Dimensions are facts, and each one carries its source. Nothing is collected in bulk from sites whose terms forbid it.
- Images are photos taken for this project, CC-licensed images with attribution, or a visitor's own upload (kept private).
- Stand-ins carry dimensions, shape and colours, never logos. The Studio pass masks the dial and case face, so a generative model never draws brand details.
- Every model and dataset is licence-checked before adoption. Anything served must have a licence that allows it, recorded in its decision record.

## 7. Phases

Steps carry IDs (2.3 is step 3 of Phase 2), so the build log and pull requests can refer to them. Phase 1's physical work (measuring, photographing, consent) runs alongside Phase 0.

| Milestone | After | What works on staging |
|---|---|---|
| **M1 First light** | Phase 3 | Photo try-on with ± mm, from upload to render |
| **M2 Full try-on** | Phase 5 | Plus Studio relighting and live AR |
| **M3 Decision help** | Phase 7 | Plus fit report, search, assistant, MCP server and swipe deck |
| **M4 Production** | Phase 9 | Public, monitored and costed (custom domain once the personal site exists) |

**Indicative timeline.** About six weeks from 27 October 2026, finishing around 11 December. Build work runs in daily sessions. The builder's hands-on tasks (measuring, photo sessions, label checks, phone tests, demo clips) add up to about 15–20 hours, most of it in Phase 1. The timeline is revisited at every milestone, and every change goes in the [change log](#10-change-log).

| Phase | Build days | Target window |
|---|---|---|
| 0 Foundations | 1–2 | 27–28 Oct |
| 1 Ground truth | 3–4, plus the builder's measuring and photo sessions | 28 Oct – 9 Nov |
| 2 Calibration | 4–5, starting on the first capture sessions | 3–9 Nov |
| 3 Rendering and the swap test (M1) | 4–5 | 10–15 Nov |
| 4 Studio | 2–3 | 16–18 Nov |
| 5 Live AR (M2) | 4–5 | 19–24 Nov |
| 6 Fit, search, assistant and MCP | 4–5 | 25–29 Nov |
| 7 Swipe recommender (M3) | 2 | 30 Nov – 1 Dec |
| 8 Product polish | 3–4 | 2–5 Dec |
| 9 Production on Google Cloud (M4) | 2–3 | 6–8 Dec |
| 10 Showcase | 2–3 | 9–11 Dec |

Most likely to stretch it: equipment delivery and the volunteers' availability (Phase 1), GPU queue times, and getting live AR right on real phones.

### Phase 0: Foundations

**Goal.** An empty but deployable system. Every part builds and tests in CI, and a hello-world web app and API are live on Cloud Run through Terraform and GitHub Actions.

- [x] 0.1 Repository, licence, README, build plan, first decision records and build log.
- [x] 0.2 Monorepo layout (§5.2) and tooling:
  - Python: a uv workspace with Python 3.12, poethepoet tasks, ruff, mypy (strict for `packages/core`) and pytest.
  - Web: pnpm with the current Node LTS, TypeScript in strict mode, ESLint and Prettier.
  - Pre-commit hooks, including a secret scan.
  - Recorded as [ADR-0007](decisions/0007-tooling-and-workflow.md) (tooling and workflow).
- [x] 0.3 CI on GitHub Actions: Python and web jobs with path filters and caching; Dependabot for pip, npm and Actions.
- [x] 0.4 Cloud bootstrap:
  - Google Cloud: a dedicated project for Lug to Lug with its own budget alerts, then APIs, Artifact Registry, Terraform state bucket, Workload Identity Federation for GitHub Actions, least-privilege service accounts, Secret Manager.
  - A Neon project with pgvector (AWS Singapore, Neon's closest region to `asia-south1`).
  - A Modal workspace, with its token in Secret Manager.
- [x] 0.5 Walking skeleton: FastAPI `/health` and a Next.js landing page, each with a Dockerfile, deployed to staging Cloud Run services from Actions, with a smoke test.
- [x] 0.6 Project page skeleton on GitHub Pages ([live](https://vinayakmokashi.github.io/lug-to-lug/)).

**Exit.** CI is green on `main`, the staging URLs respond, and `terraform plan` is clean.

### Phase 1: Ground truth

**Goal.** Measured watches, consented wrist photos, annotations, a cited catalogue and a frozen test split, all before any model work.

- [x] 1.1 Capture protocol ([`docs/data/capture-protocol.md`](data/capture-protocol.md)):
  - equipment;
  - phone settings (main lens, fixed zoom, no portrait mode);
  - stand placement, poses and lighting;
  - file naming and a session sheet;
  - the [consent form](data/consent-form.md) and the [data card skeleton](cards/benchmark-data-card.md).
- [ ] 1.2 Measure the reference watches (35 to start) three times each into `data/catalogue/reference.csv`, with a repeatability note.
- [ ] 1.3 Product photos of the reference watches: front-on, neutral background, ruler in frame.
- [ ] 1.4 Capture sessions:
  - the builder's wrist with every reference watch, across poses and lighting;
  - the three volunteers' wrists wearing the reference watches (about 10 photos to start);
  - a smaller set on everyday surfaces (desk, fabric);
  - tape and caliper measurements for every wrist.
- [ ] 1.5 Labelling tool (internal):
  - case outline points, wrist edges and watch identity;
  - model-proposed outlines that a person corrects;
  - provenance recorded per label.
- [ ] 1.6 Splits by watch and by person. The test manifest (hashes) is committed before any tuning, recorded in a decision record (evaluation splits).
- [ ] 1.7 Catalogue v0:
  - the measured reference watches plus about 300 popular references with published dimensions, each field cited;
  - a stand-in specification schema (shape, bezel, crown, colours) shared by Python and TypeScript.
- [ ] 1.8 Synthetic data v0 (training only): wrists of varied skin tones and sizes wearing parametric watches, with exact masks, scale and pose labels.

**Exit.** The data card is published, the test manifest is frozen, catalogue v0 is loaded into Postgres, and a first statistics note on the data exists.

### Phase 2: Calibration

**Goal.** Scale and wrist pose from the worn watch, with error bars that hold up; the worn watch identified; the wrist measured.

- [ ] 2.1 Baselines for the case outline, measured on dev: edges with a robust ellipse fit, and a promptable segmenter (for example SAM 2) followed by an ellipse fit.
- [ ] 2.2 A StarDist model for cases and dials:
  - covers star-convex shapes: round, cushion, tonneau and rounded square;
  - trained on synthetic plus real training photos;
  - compared with the baselines by paired test, and the winner recorded in a decision record.
- [ ] 2.3 From ellipse to pose and scale:
  - the circle's pose from its image conic, with the two-fold ambiguity resolved by the wrist's direction;
  - millimetres per pixel at the case top;
  - a correction for case thickness.
- [ ] 2.4 Uncertainty: Monte Carlo over the outline points and the catalogue's dimension tolerance gives the ± mm. A check confirms the stated intervals cover the truth at their nominal rate.
- [ ] 2.5 Identify the worn watch, measured as top-k on dev:
  - a vision model reads the dial text into a schema, with self-consistency over several reads;
  - image search over catalogue photos, with an embedder fine-tuned contrastively on the reference watches' photos;
  - hybrid search on reference numbers;
  - the user confirms.
- [ ] 2.6 Fallback references: coins of known diameter and ID-1 payment cards (85.60 × 53.98 mm), detected and posed the same way.
- [ ] 2.7 Wrist measurement:
  - wrist segmentation, width at the watch and flat-top width;
  - a circumference model fitted to tape measurements and validated across people;
  - hand breadth, for live AR.
- [ ] 2.8 Report (`docs/eval/calibration.md`) with intervals and slices. Sizing targets for later phases are set from it.

**Exit.** `packages/core` exposes calibration with tests, the report is published, and a calibration endpoint is live on staging.

### Phase 3: Rendering and the swap test

**Goal.** A believable, true-to-scale composite on a CPU, and the benchmark that proves its size. This phase reaches milestone **M1**.

- [ ] 3.1 A 2.5-D stand-in renderer built from the specification schema: round, cushion, tonneau and square cases; bezel types; lugs; crown; strap or bracelet.
- [ ] 3.2 Product-photo mode: cut the reference watches out of their product photos, keep the case and dial as real pixels, and align using the product photo's own ellipse.
- [ ] 3.3 Posing: project with the calibrated homography; the strap follows the wrist's edges; a lug-curvature model.
- [ ] 3.4 Remove the old watch with LaMa inpainting on the CPU (ONNX), with mask dilation and failure checks.
- [ ] 3.5 Match lighting and colour, then add a contact shadow. The harmonisation model is either a lightweight licence-checked one, or one trained on self-supervised pairs made from real wrist photos.
- [ ] 3.6 Swap-test harness: render B from A for every same-pose pair and report diameter error, IoU and galleries. A small subset runs in CI as an eval gate.
- [ ] 3.7 Critic: geometry checks (scale consistency, the watch inside the wrist mask, strap continuity) plus a vision-model check for gross failures. It re-renders or declines.
- [ ] 3.8 Latency per stage at Cloud Run's CPU and memory settings; quantise or shrink models where needed.
- [ ] 3.9 Web slice: upload, confirm the worn watch, pick a target, and see the render with its ± mm.

**Exit.** `docs/eval/swap-tests.md` v1 is published, p95 latency is measured, and M1 runs on staging.

### Phase 4: Studio

**Goal.** Photoreal relighting that never changes the size or the dial.

- [ ] 4.1 Base model and mask policy:
  - an inpainting or relighting base model whose licence allows serving;
  - the dial and case face are locked; only edges, shadows, strap and light may change.
- [ ] 4.2 LoRA fine-tune on consented wrist photos (Modal GPU), with a training data card.
- [ ] 4.3 Serving: a Modal endpoint that scales to zero, a job queue, results in Cloud Storage and polling; per-visitor and global daily caps.
- [ ] 4.4 Geometry tests: swap-test metrics must not move after Studio, and dial pixels stay unchanged (difference test).
- [ ] 4.5 Realism: pairwise preference against the CPU render, a vision-model judge, and cost and latency per render.
- [ ] 4.6 Web slice: a Studio button with a progress state.

**Exit.** The Studio report is published and the caps are live on staging.

### Phase 5: Live AR

**Goal.** The watch on the wrist in the phone camera, at true scale, rendered on the device. This phase reaches milestone **M2**.

- [ ] 5.1 A 3-D stand-in in React Three Fiber, generated from the same specification schema, with materials for steel, gold, ceramic and sapphire.
- [ ] 5.2 MediaPipe hand landmarks on the device, giving the wrist's anchor and orientation, with jitter smoothing (One Euro filter).
- [ ] 5.3 Scale from the hand breadth measured in the still photo; a wrist occluder; lighting estimated from the frame.
- [ ] 5.4 Contract test: the 3-D stand-in's frontal render and the 2.5-D renderer agree on dimensions within tolerance.
- [ ] 5.5 Devices and performance:
  - a device matrix (Android Chrome, iOS Safari, a mid-range phone);
  - a performance budget of at least 24 frames per second;
  - a fallback to the photo try-on.
- [ ] 5.6 Measure the live-AR scale error against the still photo, and show it on the live view.

**Exit.** Live AR runs on staging with its accuracy note.

### Phase 6: Fit, search, assistant and MCP

**Goal.** Turn a render into a decision.

- [ ] 6.1 Fit report:
  - lug overhang (lug-to-lug against the flat wrist width), thickness and case-to-wrist ratio;
  - visual size (dial opening and bezel);
  - comparison with the watches a user owns;
  - rules checked against hand judgments of fit on the reference watches.
- [ ] 6.2 Plain-English search by dimensions with [text2sql-analyst](https://github.com/VinayakMokashi/text2sql-analyst):
  - a Postgres executor contributed upstream;
  - value linking for nicknames ("BB58", "Speedy", "Sub");
  - guardrails;
  - an SQL evaluation set.
- [ ] 6.3 Sizing knowledge base from cited sources, with hybrid search and reranking. Answers cite their sources, and faithfulness is evaluated.
- [ ] 6.4 Assistant (LangGraph):
  - routing, and a planner for multi-step requests;
  - the app's tools;
  - memory of the wrist profile and the collection;
  - confirmation before saving anything;
  - a task evaluation set and agent metrics.
- [ ] 6.5 MCP server:
  - tools, plus resources (a specification page per watch) and prompts (compare two watches);
  - Streamable HTTP with token auth;
  - tested from a standard MCP client.
- [ ] 6.6 Langfuse traces and cost per conversation.
- [ ] 6.7 Web slice: fit report panel, search box and assistant chat.

**Exit.** Evaluation reports for search, the assistant and the fit rules are published, and the MCP server works from a client.

### Phase 7: Swipe recommender

**Goal.** Learn size and style preferences from swipes, and recommend. This phase reaches milestone **M3**.

- [ ] 7.1 Candidates: references whose size suits the measured wrist, with diversity constraints.
- [ ] 7.2 Features: size relative to the wrist, and style embeddings from images and descriptions.
- [ ] 7.3 Preference model:
  - Bayesian logistic regression on likes and dislikes, and Bradley–Terry when two watches are compared;
  - Thompson sampling chooses the next card, with exploration that decays;
  - a cold-start prior from the fit rules.
- [ ] 7.4 Offline evaluation with simulated users and real swipes on the reference watches: held-out AUC, and swipes until preferences settle.
- [ ] 7.5 Web slice: a deck of cards, each rendered on the user's own wrist at true size.

**Exit.** The recommender report is published.

### Phase 8: Product polish

**Goal.** One polished, mobile-first app.

- [ ] 8.1 Design system and accessibility (WCAG 2.2 AA).
- [ ] 8.2 Guided capture: a camera overlay with live checks for blur, angle and light, plus the coin and card flow.
- [ ] 8.3 Results: a before/after slider, comparison of up to three watches, and sharing a render.
- [ ] 8.4 "My collection", with optional sign-in through Firebase Authentication.
- [ ] 8.5 "Real or Rendered?": a game that collects visitors' judgments, with a consent notice.
- [ ] 8.6 Privacy screens: what is stored, and delete my data.
- [ ] 8.7 Tests: component tests, Playwright end-to-end tests on phone viewports, and Lighthouse budgets; plus a usability pass with volunteers.

**Exit.** End-to-end tests are green, and every usability finding is fixed or logged.

### Phase 9: Production on Google Cloud

**Goal.** Production-grade, cheap, observable and reversible. This phase reaches milestone **M4**.

- [ ] 9.1 Terraform for every resource:
  - Cloud Run services (web, API, MCP), service accounts and Artifact Registry;
  - Cloud Storage with lifecycle rules, and Secret Manager;
  - Cloud Scheduler for the nightly evaluation;
  - uptime checks, alert policies and budgets.
- [ ] 9.2 Delivery: build, staging, smoke tests and the eval gate, a canary traffic split, then production. Roll back by revision, with runbooks.
- [ ] 9.3 A custom domain with HTTPS once the builder's personal site exists: a subdomain of it, through Cloud Run domain mapping if the region supports it and Firebase Hosting in front otherwise. Caching for static assets. Until then, the Cloud Run and GitHub Pages addresses serve.
- [ ] 9.4 Security: upload validation (type, size, decompression bombs), rate limits, CORS and CSP, dependency and container scanning, and a secret-rotation runbook.
- [ ] 9.5 A load test with k6 to set concurrency, CPU, memory and minimum instances, and to decide whether the demo path stays warm.
- [ ] 9.6 A cost review against the budget (§8).

**Exit.** The production URL is live, with SLOs and a cost dashboard in place.

### Phase 10: Showcase

**Goal.** The public story, told with measured numbers.

- [ ] 10.1 Project page and write-up:
  - the sizing problem, and the watch on your wrist as a ruler;
  - the benchmark, with intervals and slices;
  - the three render paths and the architecture;
  - latency, monthly cost and limitations.
- [ ] 10.2 Demo media: short clips of the photo try-on, Studio and live AR.
- [ ] 10.3 Open artefacts:
  - the stand-in specification and renderer as a package, and model cards;
  - benchmark annotations, with images only where each person opted in;
  - the MCP server in public registries;
  - an optional Hugging Face Space for the CPU demo.
- [ ] 10.4 Final README pass, with credits to prior work.

**Exit.** Everything is published.

## 8. Budget

The working budget is about $50. Spending more needs a measured result that justifies it.

| Item | Expected cost | Notes |
|---|---|---|
| Digital calipers, soft tape, phone stand | $10–20, once | Skip anything already at hand |
| Modal | $0–15 | The included monthly credit covers Studio serving at demo traffic; extra spend only for LoRA training bursts ([ADR-0005](decisions/0005-gpu-on-modal.md)) |
| Kaggle | $0 | Free GPU hours for experiments |
| Google Cloud | $0 while the free-trial credit lasts, then within the free tiers | Budget alerts from the first day; see §9 on the trial |
| Neon Postgres | $0 | Free plan |
| Language and vision models | $0–5 | Groq's free tier; Gemini on the cloud credit |
| Langfuse | $0 | Free tier |
| Domain | $0–15 a year | Or a subdomain of an existing site |

Expected total: about $25–45.

## 9. Prerequisites and risks

**Prerequisites:**

- Accounts: GitHub, a Google Cloud project with billing and the free-trial credit, Neon, Modal, Groq and Kaggle.
- Equipment, for Phase 1:
  - **Digital calipers:** stainless steel, 0.01 mm resolution, 150 mm range. A strip of painter's tape on each jaw protects the watches; zero the calipers with the tape on.
  - **Soft tape measure** with millimetre markings.
  - **Overhead phone mount:**
    - rigid, holding the phone about 25–40 cm above the wrist;
    - points straight down, and locks at about 20° and 40° of tilt;
    - a desk-clamp articulated arm or a tripod with a horizontal arm both work; a floppy gooseneck does not;
    - with a Bluetooth shutter remote, so the phone is never touched between shots.
  - **Backdrop:** matte mid-grey, about A2. Neutral grey keeps exposure and white balance steady. White makes polished steel and white dials blow out, black swallows dark dials and straps, skin-like beige or wood tones confuse wrist segmentation, and a glossy surface reflects into the crystal.
  - **A steel ruler** with millimetre marks, for the product photos.
- Consent from each volunteer before their first photo.

| Risk | Mitigation |
|---|---|
| The reference case is hard to find (domed crystals, wide bezels, unusual shapes) | Use whichever outline is known (case or bezel); coin and card fallback; decline when unsure |
| Wrist curvature and steep camera angles | A curvature correction fitted on swap tests; the capture screen guides the angle |
| Missing dimensions (lug-to-lug and thickness are often unpublished) | A source and a confidence level per field; reference watches measured by hand; unknowns shown as unknown |
| Few volunteers and narrow diversity | Synthetic data for training; coverage reported per slice; more consented volunteers over time |
| Prior work exists (brand try-ons, consumer apps) | Lead with measured accuracy and calibration from the worn watch; credit prior work |
| Brand marks | Stand-ins without logos; photos taken for this project; the dial locked in Studio |
| GPU cost | CPU by default; Studio optional and capped |
| Google Cloud free trial: no GPUs, and it ends | GPU work on Modal and Kaggle; upgrade the billing account before the trial ends, to keep the remaining credit; services scale to zero |
| Live AR too slow on older phones | A performance budget and a fallback to the photo try-on |
| Privacy | Consent, minimal retention, EXIF stripping, deletion on request |
| Scope | Every phase ships a working slice; stretch items are marked |

## 10. Change log

| Date | Change | Why |
|---|---|---|
| 2026-10-26 | Plan created | [ADR-0001](decisions/0001-choose-lug-to-lug.md) |
| 2026-10-26 | Google Cloud, Next.js and Modal chosen; live AR in the first release | [ADR-0003](decisions/0003-deploy-on-google-cloud.md), [ADR-0004](decisions/0004-web-stack.md), [ADR-0005](decisions/0005-gpu-on-modal.md), [ADR-0001](decisions/0001-choose-lug-to-lug.md) |
| 2026-10-26 | A dedicated Google Cloud project with its own budget alerts | Keeps this project's costs, permissions and quotas apart from anything else on the account |
| 2026-10-26 | The custom domain waits for the builder's personal site | The site doesn't exist yet; the Cloud Run and GitHub Pages addresses serve until then |
| 2026-10-26 | Two volunteers under pseudonymous IDs; equipment specified; a capture set on everyday surfaces | [ADR-0006](decisions/0006-data-consent-and-privacy.md)'s privacy rules; swap tests need a pose that stays fixed; studio-only photos would flatter the benchmark |
| 2026-10-26 | Indicative timeline added (about 12 weeks) | To plan the milestones and compare the plan with what actually happens |
| 2026-10-26 | A third volunteer (P04) | A wider range of wrists in the benchmark |
| 2026-10-26 | Timeline tightened to about six weeks | Build work runs in daily sessions; the builder's hands-on time, about 15–20 hours, is concentrated in Phase 1 |
| 2026-10-27 | ADR-0008 records the infrastructure layout; the evaluation-splits record (step 1.6) takes the next free number | The infrastructure decision came first, in step 0.4 |
| 2026-10-28 | ADR-0009 records the catalogue and the stand-in specification; the reference watches' measuring adds the case length of non-round cases and the case material | Three parts of the system draw the same watch, and the stand-ins need both |

## 11. Status tracker

| Phase | Status | Started | Finished |
|---|---|---|---|
| 0 Foundations | Done | 2026-10-26 | 2026-10-28 |
| 1 Ground truth | In progress (step 1.1 done) | 2026-10-27 | |
| 2 Calibration | Planned | | |
| 3 Rendering and the swap test | Planned | | |
| 4 Studio | Planned | | |
| 5 Live AR | Planned | | |
| 6 Fit, search, assistant and MCP | Planned | | |
| 7 Swipe recommender | Planned | | |
| 8 Product polish | Planned | | |
| 9 Production on Google Cloud | Planned | | |
| 10 Showcase | Planned | | |
