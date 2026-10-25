# ADR-0001: Build Lug to Lug, a true-to-scale watch try-on with measured sizing

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

The most common question before buying a watch online is whether it will fit. Case diameter alone does not answer it: lug-to-lug length, thickness, case shape and the wearer's wrist decide how a watch wears. Most watches are bought without trying them on.

Virtual try-ons already exist, from brand-facing services to consumer apps. They either infer the scale from the image or ask the user to place the watch by hand, and none of them publishes how accurate its sizing is.

A set of reference watches, each measured with calipers, and photos of several people's wrists wearing them in the same pose give ground truth for sizing without special equipment.

## Decision

Build **Lug to Lug**:

1. **Calibrate from the watch the user already wears.** A round case of known diameter appears as an ellipse in a photo; the ellipse gives the scale and the tilt of the wrist. A coin or a payment card is the fallback.
2. **Render any watch at true size**, labelled with its own ± mm, on a CPU by default. An optional GPU pass relights the result without changing the dial or the size.
3. **Prove the sizing** with swap tests on a held-out benchmark of real photos (render watch B from a photo of watch A, compare with a real photo of B).
4. **Help people decide:** a fit report, search by dimensions in plain English, a swipe recommender, an assistant with cited answers, and an MCP server.
5. **Ship live AR in the first release**, rendered on the visitor's device.

The name is the measurement that most often decides fit.

## Consequences

- Data collection (measurements, photos, consent) comes first and gates the model work.
- Every accuracy claim comes from the benchmark, with confidence intervals; the README and project page carry no unmeasured claims.
- The project needs computer vision, generative models, recommendation, an agent and cloud delivery working together, so each phase ships a working slice rather than a component in isolation.

## Alternatives considered

These are the ways of getting the scale that were weighed against calibrating from the worn watch:

- **Ask for the wrist size and let the user place the watch by hand:** quick, but it depends on the user's own measuring and placement, and its error cannot be stated.
- **Require a card or coin in every photo:** a reliable scale, but it adds a step to every try-on and sits beside the wrist rather than on it. Kept as the fallback.
- **Infer the scale from hand landmarks alone:** needs no reference, but hand proportions vary too much between people for millimetre accuracy. Used only in live AR, after a calibrated photo has measured the user's own hand.
- **Generate the try-on with a generative model alone:** realistic, but nothing guarantees the size, which is the question being answered.
