# Data

Numbers, schemas and manifests only. **Photos never enter this repository** ([ADR-0006](../docs/decisions/0006-data-consent-and-privacy.md)); a pre-commit hook rejects image files under `data/`.

| Path | What | Phase |
|---|---|---|
| `catalogue/reference.csv` | The reference watches, measured three times each with calipers | 1.2 |
| `catalogue/` | About 300 popular references with published dimensions, every field cited ([rules](catalogue/README.md)) | 1.7 |
| `schemas/` | The data contracts, shared by Python and TypeScript: the stand-in specification, the catalogue entry and the image annotation ([ADR-0009](../docs/decisions/0009-catalogue-and-stand-in-specification.md)) | 1.7 |
| `manifests/` | Capture-session manifests and the frozen test split (file hashes) | 1.4, 1.6 |

People appear only as pseudonymous IDs (P01, P02, …). The data records measurements, never who owns a watch.
