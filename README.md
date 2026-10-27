# Lug to Lug

**Try any watch on your own wrist at true size, with the error bar to prove it.**

> **Status: building (Phase 1, ground truth).** The foundations are done, and the deployment skeleton is live: a [project page](https://vinayakmokashi.github.io/lug-to-lug/) and a staging [web app](https://web-staging-cb3gjlkxbq-el.a.run.app) with its [API](https://api-staging-cb3gjlkxbq-el.a.run.app/health). Nothing below is measured yet; results will appear here as they land, each with its confidence interval. Progress is tracked in the [build plan](docs/PLAN.md#11-status-tracker).

Lug to Lug is a true-to-scale watch try-on. You photograph your wrist wearing any watch you already own. The app recognises that watch, looks up its case diameter and uses it as a ruler to measure your wrist. Then it shows any other watch on your wrist at its real size, labels the render with its sizing error, and tells you how the watch will fit.

## Why

Case diameter alone says little about how a watch wears. Lug-to-lug length, thickness, case shape and the width of your wrist decide whether it fits, and most watches are bought online without trying them on. Existing virtual try-ons infer the scale from the image or ask you to place the watch by hand, and none of them publishes how accurate its sizing is.

## How it will work

1. **The watch you wear is the ruler.** A round case of known diameter appears as an ellipse in a photo. The ellipse gives the scale (pixels per millimetre) and the tilt of your wrist. A coin or a payment card works when you have no watch on.
2. **Measure the wrist:** width at the watch, the flat top of the wrist that the lugs sit on, and an estimate of the circumference.
3. **Render the new watch at true size.** It is drawn as a stand-in from the watch's published dimensions, or from a real product photo, and posed onto your wrist. Your old watch is painted out and the lighting is matched. Everything runs on a CPU; an optional GPU pass relights the result without touching the dial.
4. **Report the fit:** lug overhang (lug-to-lug against the flat top of the wrist), thickness, and how large it wears next to the watches you own.
5. **Help you decide:**
   - plain-English search by dimensions;
   - a swipe deck that learns your size and style;
   - an assistant that answers sizing questions with sources;
   - an MCP server, so other AI applications can use the same tools.
6. **Live preview:** an augmented-reality view in the phone browser, rendered on your device.

## How the sizing will be measured

The swap test:

1. Photograph a wrist wearing watch A, then watch B, in the same pose.
2. Render B from the photo of A.
3. Compare the render with the real photo of B: diameter error in millimetres and outline overlap.

The benchmark uses a set of reference watches measured with calipers (35 to start) and several volunteers' wrists. It is split by watch and by person, and the test set is frozen before any tuning. Results are reported by pose, lighting, skin tone and wrist size.

## Planned stack

| Part | Tools |
|---|---|
| Web app | Next.js with React Three Fiber |
| Live AR | MediaPipe hand tracking |
| Services | FastAPI on Google Cloud Run |
| Database | Postgres with pgvector on Neon |
| GPU work | Modal |
| Delivery | Terraform and GitHub Actions |

## Repository

| Path | What |
|---|---|
| `apps/web` | Next.js web app |
| `services/api` | FastAPI service |
| `packages/core` | Calibration, wrist measurement and rendering (Python) |
| `services/mcp`, `services/studio` | MCP server and GPU relighting (later phases) |
| `ml/`, `eval/` | Training code and the evaluation harness (later phases) |
| `data/` | Measurements, schemas and manifests; never photos |
| `infra/terraform` | Every Google Cloud resource |
| `docs/` | Plan, decisions, build log, runbooks, project page |

To set up and run the checks locally, see [local development](docs/runbooks/local-development.md).

## Documents

- [Build plan](docs/PLAN.md): definition of done, phases and steps, budget, risks, status tracker
- [Decision records](docs/decisions/README.md)
- [Build log](docs/BUILD_LOG.md)
- Runbooks: [local development](docs/runbooks/local-development.md), [deploy and roll back](docs/runbooks/deploy.md)
- [Project page](https://vinayakmokashi.github.io/lug-to-lug/)

## Data and privacy

- Every person photographed for the benchmark gives written consent.
- Raw photos never enter this repository; it holds manifests, annotations and measured numbers only.
- Uploads to the app are processed in memory and stripped of location data. They are saved only when you ask, and never used for training without opt-in.

See [ADR-0006](docs/decisions/0006-data-consent-and-privacy.md).

## Licence

[MIT](LICENSE). Brand names identify watches and their published dimensions; the app does not render brand logos.
