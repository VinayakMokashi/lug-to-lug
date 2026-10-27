# lugtolug-core

The measuring and rendering core of Lug to Lug, used inside the API:

- calibration: the worn watch's case ellipse gives the scale and the wrist's tilt, with ± mm;
- wrist measurement: width at the watch, flat-top width, a circumference estimate;
- stand-in specifications and the 2.5-D renderer;
- compositing and the fit rules.

Type-checked with mypy in strict mode. Each module arrives with its phase in the [build plan](../../docs/PLAN.md).
