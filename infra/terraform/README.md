# Infrastructure

Every Google Cloud resource, in Terraform. The design is in [ADR-0008](../../docs/decisions/0008-infrastructure-and-delivery.md); how to apply it is in the [deploy runbook](../../docs/runbooks/deploy.md).

| Path | What | State prefix |
|---|---|---|
| `bootstrap/` | APIs, the monthly budget, the state bucket, the image registry, workload identity federation for GitHub Actions, service accounts, empty secrets | `bootstrap` |
| `envs/staging/` | The staging API and web app on Cloud Run | `envs/staging` |
| `modules/cloud-run-service/` | A Cloud Run service that scales to zero; Terraform owns its configuration, the deploy workflow owns its image | |

State lives in the versioned bucket `gs://lug-to-lug-tfstate`. CI checks formatting and validates every root; applies are done by hand by the project owner.
