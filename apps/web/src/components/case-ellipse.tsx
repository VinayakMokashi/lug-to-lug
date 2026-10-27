/**
 * A round case seen on a tilted wrist. Rolling the wrist foreshortens the case across
 * the arm (3 to 9 o'clock) and leaves it full length along the arm (12 to 6), so the
 * circle becomes an ellipse. The long axis carries the known diameter, which sets the
 * scale; the ratio of the axes gives the tilt (cos 45° ≈ 0.71).
 */
export function CaseEllipse() {
  const cx = 150;
  const cy = 110;
  const a = 84; // semi-major axis (along the arm), px
  const b = 59; // semi-minor axis (across the arm), px: b / a ≈ 0.70

  return (
    <svg
      viewBox="0 0 345 220"
      role="img"
      aria-labelledby="case-ellipse-title"
      className="w-full max-w-md text-foreground"
    >
      <title id="case-ellipse-title">
        A round watch case appears as an ellipse on a tilted wrist. Its long
        axis is the known diameter and sets the scale; the ratio of the axes
        gives the tilt.
      </title>
      {/* Strap along the arm */}
      <rect
        x={cx - 30}
        y={0}
        width={60}
        height={34}
        rx={6}
        className="fill-line"
      />
      <rect
        x={cx - 30}
        y={186}
        width={60}
        height={34}
        rx={6}
        className="fill-line"
      />
      {/* Lugs */}
      {[-1, 1].map((side) =>
        [-1, 1].map((end) => (
          <rect
            key={`${side}${end}`}
            x={cx + side * 26 - 5}
            y={end < 0 ? cy - a - 14 : cy + a - 6}
            width={10}
            height={20}
            rx={3}
            className="fill-muted"
          />
        )),
      )}
      {/* Case and dial */}
      <ellipse
        cx={cx}
        cy={cy}
        rx={b}
        ry={a}
        className="fill-background stroke-foreground"
        strokeWidth={3}
      />
      <ellipse
        cx={cx}
        cy={cy}
        rx={b - 9}
        ry={a - 13}
        className="fill-none stroke-line"
        strokeWidth={2}
      />
      <line
        x1={cx}
        y1={cy}
        x2={cx}
        y2={cy - a + 26}
        className="stroke-foreground"
        strokeWidth={3}
        strokeLinecap="round"
      />
      <line
        x1={cx}
        y1={cy}
        x2={cx + 28}
        y2={cy + 14}
        className="stroke-foreground"
        strokeWidth={3}
        strokeLinecap="round"
      />
      <circle cx={cx} cy={cy} r={3.5} className="fill-accent" />
      {/* Long axis: the known diameter */}
      <g className="stroke-accent" strokeWidth={1.5}>
        <line x1={cx + b + 22} y1={cy - a} x2={cx + b + 22} y2={cy + a} />
        <line x1={cx + b + 16} y1={cy - a} x2={cx + b + 28} y2={cy - a} />
        <line x1={cx + b + 16} y1={cy + a} x2={cx + b + 28} y2={cy + a} />
        <line
          x1={cx + b + 4}
          y1={cy - a}
          x2={cx + b + 14}
          y2={cy - a}
          strokeDasharray="2 3"
        />
        <line
          x1={cx + b + 4}
          y1={cy + a}
          x2={cx + b + 14}
          y2={cy + a}
          strokeDasharray="2 3"
        />
      </g>
      <text
        x={cx + b + 34}
        y={cy - 4}
        className="fill-accent font-mono"
        fontSize={13}
      >
        Ø 40 mm
      </text>
      <text
        x={cx + b + 34}
        y={cy + 13}
        className="fill-muted font-mono"
        fontSize={10}
      >
        known: the scale
      </text>
      {/* Short axis: the tilt */}
      <line
        x1={cx - b}
        y1={cy}
        x2={cx + b}
        y2={cy}
        className="stroke-muted"
        strokeWidth={1.2}
        strokeDasharray="4 4"
      />
      <text x={8} y={cy - 4} className="fill-muted font-mono" fontSize={10}>
        b / a = 0.70
      </text>
      <text x={8} y={cy + 11} className="fill-muted font-mono" fontSize={10}>
        tilt ≈ 45°
      </text>
    </svg>
  );
}
