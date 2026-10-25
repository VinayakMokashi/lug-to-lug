# ADR-0003: Deploy on Google Cloud with services that scale to zero

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

The app must be public, on HTTPS, defined as code, and cheap to keep online: a demo that costs nothing while nobody is using it. Google Cloud's free-trial credit is available for the build.

## Decision

- **Compute:** Cloud Run for the web app, the API and the MCP server. Services scale to zero and serve HTTPS on their Cloud Run addresses; a custom domain is added in Phase 9.
- **Supporting services:** Artifact Registry for container images, Secret Manager for keys, Cloud Storage for model artefacts and for renders a visitor chooses to save (deleted by lifecycle rules), Cloud Scheduler for the nightly evaluation job.
- **Database:** Postgres with pgvector on Neon's free plan. It is serverless and suspends when idle, so it avoids the standing cost of a Cloud SQL instance. The Neon region nearest to the Cloud Run region is chosen in Phase 0.
- **Region:** `asia-south1` (Mumbai), closest to the builder and the first users.
- **Delivery:** every resource in Terraform. GitHub Actions deploys through Workload Identity Federation, so no service-account key exists anywhere.
- **Cost guard:** budget alerts are created before any other resource.

## Consequences

- The free trial does not allow GPUs, so GPU work runs elsewhere ([ADR-0005](0005-gpu-on-modal.md)).
- The billing account must be upgraded to a paid account before the trial ends, to keep the resources running and any remaining credit.
- Cold starts on the demo path are measured in Phase 9. Keeping one instance warm is a costed decision made then, not a default.

## Alternatives considered

- **AWS (App Runner or ECS, RDS):** comparable, but no credit at hand for this project.
- **Vercel for the web app:** the simplest host for Next.js, but it splits the platform, the access control and the billing in two.
- **Cloud SQL:** a managed Postgres in the same cloud, with a standing monthly cost even when idle.
