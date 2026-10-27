# Deploy, roll back and change the infrastructure

How the services reach Google Cloud, and what to do by hand when needed. The design is in [ADR-0008](../decisions/0008-infrastructure-and-delivery.md).

| | |
|---|---|
| Project | `lug-to-lug` |
| Region | `asia-south1` (Mumbai) |
| Images | `asia-south1-docker.pkg.dev/lug-to-lug/lug-to-lug/<service>:<commit>` |
| Staging API | `api-staging` on Cloud Run |
| Staging web app | `web-staging` on Cloud Run |
| Budget | $10 a month, measured before credits; alerts at 50%, 90% and 100% of actual spend and 100% of forecast |

## How a deploy happens

Every push to `main` runs [CI](../../.github/workflows/ci.yml). When the checks pass, each service whose files changed is deployed by [deploy-service.yml](../../.github/workflows/deploy-service.yml):

1. GitHub's OIDC token is exchanged for a short-lived token of `github-deployer`. No key is stored anywhere.
2. The image is built with the commit baked in (`GIT_SHA`), and pushed.
3. `gcloud run services update <service>-staging --image=…` rolls out a new revision, which takes all the traffic.
4. Smoke tests: `/health` must report this commit, and the web app's `/status` page must reach the API.

The API deploys first, then the web app.

"Changed" means changed since the last commit whose CI run on `main` passed, not only since the previous push. Runs on `main` queue one behind the other, and GitHub cancels a run that is still waiting when a newer one arrives. Measuring from the last green commit means the newer run picks up the cancelled run's changes, so no change is left unchecked or undeployed.

**To deploy without a change:** on GitHub, open Actions → CI → Run workflow, on `main`, with "Deploy both services" ticked.

## Roll back

A rollback moves traffic to an earlier revision; nothing is rebuilt.

```bash
gcloud run revisions list --service=api-staging --region=asia-south1 --project=lug-to-lug
gcloud run services update-traffic api-staging --to-revisions=<revision>=100 \
  --region=asia-south1 --project=lug-to-lug
```

The next deploy sends traffic to the newest revision again. To do that by hand: `gcloud run services update-traffic api-staging --to-latest …`.

## Change the infrastructure

Applied by hand by the project owner. Terraform authenticates with the owner's `gcloud` login, so no key file is needed:

```bash
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)   # valid for an hour
export TF_VAR_billing_account=<billing account ID>                    # bootstrap only; never committed

terraform -chdir=infra/terraform/bootstrap init
terraform -chdir=infra/terraform/bootstrap plan -out=bootstrap.tfplan
terraform -chdir=infra/terraform/bootstrap apply bootstrap.tfplan
```

The same for `infra/terraform/envs/staging` (it needs no billing account). A deploy changes only the image, which Terraform ignores, so a plan right after a deploy should say "No changes".

## Add or rotate a secret value

Secrets are created empty by Terraform; values never pass through Terraform. From a `.env` file, without printing the value:

```bash
grep '^NEON_DATABASE_URL=' .env | cut -d= -f2- | tr -d '\r\n' \
  | gcloud secrets versions add neon-database-url --data-file=- --project=lug-to-lug
```

A service reads a secret only after its runtime account is granted `roles/secretmanager.secretAccessor` on that one secret, in Terraform. After a rotation, disable the old version: `gcloud secrets versions disable <version> --secret=<name>`.

## Costs

Everything scales to zero, and staging is capped at two instances per service. Expected idle cost is about $0 within the free tiers. Image storage is kept small by cleanup rules: the five newest versions of each image are kept, and anything older than a week is deleted. If a budget alert arrives, check Cloud Run's request counts and Artifact Registry's storage first.
