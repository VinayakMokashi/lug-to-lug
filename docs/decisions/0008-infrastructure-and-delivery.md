# ADR-0008: Infrastructure layout and keyless delivery

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

[ADR-0003](0003-deploy-on-google-cloud.md) puts every cloud resource in Terraform and every deploy through GitHub Actions without stored keys. Three things pull in different directions:

- The project's foundations (budget, identity federation, service accounts) need owner and billing rights, and change rarely.
- The services change on every commit, and the image is only known after CI has built it.
- A few resources must exist before Terraform can run at all: the project, its billing link, the bucket that holds Terraform's state, and (by choice) the budget.

## Decision

**Two Terraform roots, one state bucket.** State lives in a versioned Cloud Storage bucket, `lug-to-lug-tfstate`, under one prefix per root.

| Root | Holds | Applied by |
|---|---|---|
| `infra/terraform/bootstrap` | APIs, the monthly budget, the state bucket, the image registry, workload identity federation, service accounts, empty secrets | The project owner, by hand, rarely |
| `infra/terraform/envs/staging` | The Cloud Run services, built from `modules/cloud-run-service` | The project owner, when a service's configuration changes |

A production root joins in Phase 9, built from the same module.

**Bootstrapping order.** The project and its billing link were created with `gcloud`. The budget came next, before any other resource. Then the state bucket was created. Terraform imports the budget and the bucket. The Resource Manager and Service Usage APIs are enabled with `gcloud` before the first plan, because Terraform needs them to read the project.

**Images belong to CI; everything else to Terraform.**
- On every push to `main` that passes the checks, CI builds `<registry>/<service>:<commit>`, pushes it and rolls it out with `gcloud run services update --image`.
- The module tells Terraform to ignore the image, so a deploy never shows up as drift and `terraform apply` never rolls a deploy back.
- The API deploys before the web app, so the web app's smoke test reaches the new API.

**The commit is baked into the image** as `GIT_SHA`. Each service's `/health` reports it, and the smoke test passes only when the live service reports the commit that was just deployed.

**Keyless deploys.**
- A workload identity pool trusts GitHub's OIDC tokens only when they come from this repository's ID, its owner's ID and the `main` branch.
- Those tokens can act as one service account, `github-deployer`. It may push images to the registry, update Cloud Run services (`roles/run.developer`, which cannot change who may call them) and act as the two runtime accounts. It can do nothing else.
- No service-account key exists.

**Runtime identities and secrets.**
- The API and the web app each run as their own service account, which starts with no roles.
- Terraform creates each secret empty. Its value is added with `gcloud secrets versions add`, so it never enters Terraform's state.
- A service is granted a secret only when it starts reading it.

**The billing account ID** is a variable passed at apply time and never committed.

**CI checks Terraform** (format and validate) on every change. A `terraform plan` in CI arrives with production in Phase 9.

## Consequences

- A rollback is a traffic switch to an earlier revision ([deploy runbook](../runbooks/deploy.md)), not a Terraform change.
- Changing a service's memory, scaling or environment is a Terraform change applied by hand. It leaves the running image alone.
- Deploys only run from `main`. Pull requests from Phase 1 on get checks but no deploy until the identity condition is widened on purpose.
- Applying `bootstrap` needs owner rights on the project and billing rights on the account; nothing in CI has either.

## Alternatives considered

- **One Terraform root:** the identity that deploys the services would also need the rights to change IAM and the budget.
- **Terraform deploys the image** (CI runs `terraform apply` with the image as a variable): CI would need access to the state and broader rights, and every deploy becomes a full plan.
- **A service-account key in a GitHub secret:** a long-lived credential that can leak; workload identity federation needs none.
- **Cloud Build triggers:** a second CI system next to GitHub Actions, which already runs the checks.
- **The `deploy-cloudrun` action:** works, but the plain `gcloud` command is explicit and is the same command the runbook uses by hand.
