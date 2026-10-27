# One-time adoption of what gcloud created before Terraform existed. Safe to keep:
# once a resource is in the state, its import block does nothing.

import {
  to = google_billing_budget.monthly
  id = "billingAccounts/${var.billing_account}/budgets/827d2144-450c-4602-87fc-16c144e3b008"
}

import {
  to = google_storage_bucket.tfstate
  id = "lug-to-lug-tfstate"
}
