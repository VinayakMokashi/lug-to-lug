# Evaluation

The harness that measures the claims:

- the **swap test**: render watch B from a photo of watch A in the same pose, then compare with the real photo of B (diameter error in mm, outline overlap);
- interval coverage: does "± x mm" contain the truth at its stated rate;
- wrist, identification, live-AR, recommender and assistant metrics.

Every rate gets a 95% bootstrap interval, and comparisons use paired tests. A small subset runs in CI as an eval gate. Reports are published in `docs/eval/`. Starts in Phase 2 ([build plan](../docs/PLAN.md#63-metrics)).
