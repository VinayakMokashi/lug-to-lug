# ADR-0005: Run GPU work on Modal and Kaggle

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

The project has two kinds of GPU work:

- **Training bursts:** segmentation fine-tunes and a LoRA for the Studio relighting model.
- **Serving:** the optional Studio relighting at demo traffic.

The development laptop has no CUDA GPU, Google Cloud's free trial does not allow GPUs, and the working budget is about $50.

## Decision

- **Modal** for Studio serving, as a web endpoint that scales to zero and is billed per second, and for training bursts that need a fast GPU. Its included monthly credit ($30 a month when this was written) covers demo traffic.
- **Kaggle's free GPU hours** for experiments that can wait.
- **Caps:** per-visitor and global daily limits on Studio jobs. The CPU render is always the default, and the API falls back to it whenever Studio is unavailable.
- **A Hugging Face Space** (ZeroGPU) may mirror the demo later for discoverability. It is not part of the serving path.

## Consequences

- Studio adds a second platform and a second secret, isolated behind one API client.
- Pricing and the included credit are re-checked at the start of Phase 4.

## Alternatives considered

- **Cloud Run GPUs:** not allowed on the free trial, and new projects may wait for GPU quota.
- **Hugging Face ZeroGPU as the main host:** quota is tied to each visitor's account, and the platform is built around Gradio apps.
- **Replicate or fal:** simple, but per-image pricing and less control over masking.
