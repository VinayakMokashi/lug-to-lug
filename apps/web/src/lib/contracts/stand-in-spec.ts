// Generated from data/schemas/stand-in-spec.schema.json by scripts/contracts.mjs.
// Do not edit: change the schema, then run `pnpm contracts`.

/**
 * Everything needed to draw a watch at its true size without brand marks: the outline, the layers seen from above, and the colours. The 2.5-D renderer, the 3-D stand-in for live AR and the synthetic data generator all draw from it. Lengths are nominal; their uncertainty lives in the catalogue.
 */
export interface StandInSpec {
  /**
   * The version of this specification format
   */
  spec_version: 1;
  case: Case;
  bezel: Bezel;
  dial: Dial;
  lugs: Lugs;
  crown: Crown;
  strap: Strap;
  /**
   * Dimensions filled with a default rather than from a measurement or a cited source, as 'section.field' paths (for example 'lugs.lug_to_lug_mm'). A render that depends on one says so. Colours, finish and markings are always approximate in a stand-in and are never listed.
   */
  assumed: string[];
}
export interface Case {
  /**
   * The case outline seen from above. 'square' covers rectangular cases too
   */
  shape: "round" | "cushion" | "tonneau" | "square" | "other";
  /**
   * Across the case body from 9 to 3 o'clock, without the crown
   */
  diameter_mm: number;
  /**
   * The case body from 12 to 6 o'clock, without the lugs. Equal to diameter_mm for a round case
   */
  length_mm: number;
  /**
   * Exponent of the superellipse that draws the outline: 2 is a circle or an ellipse, about 4 a cushion, 8 or more a square with small rounded corners
   */
  squareness: number;
  /**
   * Width at the 12 and 6 o'clock ends relative to the middle: 1 for most cases, about 0.8 for a tonneau
   */
  taper: number;
  /**
   * From the case back to the top of the crystal
   */
  thickness_mm: number;
  /**
   * How far the crystal rises above the bezel or case top; 0 for a flat crystal
   */
  crystal_dome_mm: number;
  /**
   * What the case is made of; gold covers yellow, rose and white gold, told apart by colour
   */
  material:
    "steel" | "titanium" | "gold" | "ceramic" | "resin" | "bronze" | "other";
  /**
   * How the case surface reflects light
   */
  finish: "polished" | "brushed" | "matte";
  /**
   * An sRGB colour as lower-case hex, for drawing
   */
  colour: string;
}
export interface Bezel {
  /**
   * The ring around the crystal
   */
  type: "none" | "smooth" | "fluted" | "rotating_insert" | "other";
  /**
   * Outer width of the bezel or top ring from 9 to 3 o'clock; null when there is no separate bezel
   */
  outer_mm: number | null;
  /**
   * The bezel's own colour; null when there is no separate bezel
   */
  colour: string | null;
  /**
   * Colour of a rotating bezel's insert; null for other bezels
   */
  insert_colour: string | null;
  /**
   * A generic scale drawn on the bezel. Never text or logos
   */
  markings: "none" | "minutes" | "dive" | "gmt" | "tachymeter";
}
export interface Dial {
  /**
   * Width of the visible dial opening (the inner edge of the bezel or case) from 9 to 3 o'clock. The opening follows the case outline's shape
   */
  opening_mm: number;
  /**
   * An sRGB colour as lower-case hex, for drawing
   */
  colour: string;
  /**
   * Generic hour markers. Never text or logos
   */
  index_style: "baton" | "arabic" | "roman" | "dots" | "none";
  /**
   * An sRGB colour as lower-case hex, for drawing
   */
  index_colour: string;
  /**
   * An sRGB colour as lower-case hex, for drawing
   */
  hands_colour: string;
}
export interface Lugs {
  /**
   * From the tip of the upper lugs to the tip of the lower lugs, along 12 to 6 o'clock
   */
  lug_to_lug_mm: number;
  /**
   * Inside distance between the lugs, where the strap fits
   */
  lug_width_mm: number;
  /**
   * 'integrated' when the strap or bracelet joins the case without separate lugs
   */
  style: "standard" | "integrated";
}
export interface Crown {
  /**
   * Where the crown sits, as an hour on the dial (3 for most watches, 9 for a left-hand crown)
   */
  position: number;
  /**
   * Diameter of the crown
   */
  diameter_mm: number;
  /**
   * How far the crown stands out from the case
   */
  length_mm: number;
  /**
   * Whether the case has crown guards
   */
  guards: boolean;
}
export interface Strap {
  /**
   * What the watch is worn on
   */
  type: "bracelet" | "leather" | "rubber" | "fabric" | "other";
  /**
   * An sRGB colour as lower-case hex, for drawing
   */
  colour: string;
  /**
   * Strap width at the buckle or clasp; equal to the lug width when it doesn't taper
   */
  width_at_buckle_mm: number;
}
