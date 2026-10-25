# ADR-0006: Consent, storage and retention for personal photos

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

The benchmark needs photos of real wrists. They are personal data: skin, tattoos, jewellery, and sometimes faces or rooms in the background. Visitors will upload the same kind of photo.

## Decision

### People in the benchmark

- **Consent first.** Written consent from every person before their first photo. It states the purpose (evaluation and training), whether their images may ever be published, and how to withdraw. Consent records are kept outside the repository.
- **Raw photos stay out of the repository.** They are stored in a private location; the repository holds manifests (file hashes), annotations and measured numbers only.
- **Publishing needs an opt-in.** An image is published only with that person's explicit opt-in. Withdrawal removes their images and annotations from every later release.
- **Labels record who made them:** drawn by a person, or proposed by a model and corrected by a person.

### Visitors

- Uploads are processed in memory, and EXIF data (including location) is stripped on arrival.
- Nothing is saved unless the visitor asks. Saved renders are deleted automatically after 30 days, and a delete-my-data control removes them sooner.
- Visitor uploads are never used for training or evaluation without explicit opt-in.
- Logs never contain images.

## Consequences

- The evaluation cannot be fully reproduced from the public repository unless people opt in to publishing their images. The published annotations, manifests and numbers still make the results checkable in part.
- The capture protocol and the consent form are written before the first photo (Phase 1).

## Alternatives considered

- **Collecting wrist photos from the web:** no consent and unclear licences.
