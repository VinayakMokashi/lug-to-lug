# MCP server

Gives other AI applications the same tools the web app uses, over Streamable HTTP with token auth:

- `measure_wrist`: scale, tilt and wrist measurements from a photo, with ± mm;
- `fit_check`: how a watch will fit a measured wrist;
- `try_on`: a true-to-scale render;
- `search_by_size`: plain-English search by dimensions.

It also serves a specification page per watch as a resource, and a "compare two watches" prompt. Built in Phase 6 ([build plan](../../docs/PLAN.md#phase-6-fit-search-assistant-and-mcp)).
