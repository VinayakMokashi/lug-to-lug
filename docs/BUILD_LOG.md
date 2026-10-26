# Build log

One entry per working session, newest first. Each entry records what changed, the commands and results that matter, problems met and the next steps. The plan's steps are referred to by their IDs in [PLAN.md](PLAN.md).

## 2026-10-26: Planning (step 0.1)

**What changed**

- Chose the project and its name, and wrote the build plan ([PLAN.md](PLAN.md)) and decision records 0001 to 0006.
- Created the public repository with the licence, README, `.gitignore`, `.gitattributes` and this log.
- Refined the plan:
  - a dedicated Google Cloud project with its own budget alerts;
  - two volunteers, recorded under pseudonymous IDs;
  - equipment specifications;
  - a capture set on everyday surfaces;
  - the custom domain deferred until the personal site exists;
  - an indicative timeline of about 12 weeks.

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
