# ADR-0004: Next.js for the web app, FastAPI for the services

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

The app needs a guided camera capture with overlays, touch gestures (a swipe deck, a before/after slider), a 3-D renderer and on-device hand tracking for live AR, a streaming chat, and good performance on phones. The measurement, rendering and machine-learning code is Python.

## Decision

- **Web app:** Next.js (App Router) with TypeScript in strict mode and Tailwind CSS. React Three Fiber (three.js) draws the 3-D stand-in; MediaPipe Tasks Vision tracks hand landmarks on the device.
- **Services:** Python with FastAPI for the API and the MCP server.
- **Shared contracts:** the stand-in specification and the API types are defined once as JSON Schema, and Python (Pydantic) and TypeScript types are generated from it.
- **Internal tools:** Streamlit is fine for tools only the builder uses, such as the labelling tool.

## Consequences

- One repository holds two toolchains, uv for Python and pnpm for the web app; Phase 0 sets up both in CI.
- A contract test keeps the server's 2.5-D renderer and the browser's 3-D stand-in in agreement on dimensions.

## Alternatives considered

- **Streamlit or Gradio for the product:** quick to build, but no control over camera overlays, gestures or AR.
- **A native mobile app:** the best AR, but not shareable as a link and slower to iterate.
