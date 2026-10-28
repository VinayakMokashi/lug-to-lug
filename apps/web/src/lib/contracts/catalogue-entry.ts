// Generated from data/schemas/catalogue-entry.schema.json by scripts/contracts.mjs.
// Do not edit: change the schema, then run `pnpm contracts`.

/**
 * A cited length, or null when no source gives it
 */
export type OptionalCitedLength = CitedLength | null;

/**
 * One watch reference with its published dimensions and appearance. Every value cites a source; a value no source gives is null (unknown), never guessed. This is the form the API serves; the files in data/catalogue store the same facts as rows.
 */
export interface CatalogueEntry {
  /**
   * The version of this entry format
   */
  entry_version: 1;
  /**
   * Stable ID: the brand and reference in lower case, joined by hyphens
   */
  id: string;
  brand: string;
  model: string;
  /**
   * The manufacturer's reference number
   */
  reference: string;
  /**
   * Nicknames people search with, for example a model's common short name
   */
  aliases: string[];
  /**
   * The main source: the brand, model and reference come from it, and so does any value without its own citation
   */
  source: string;
  case_shape: CitedShape;
  case_diameter_mm: OptionalCitedLength;
  case_length_mm: OptionalCitedLength;
  bezel_diameter_mm: OptionalCitedLength;
  dial_opening_mm: OptionalCitedLength;
  lug_to_lug_mm: OptionalCitedLength;
  thickness_mm: OptionalCitedLength;
  lug_width_mm: OptionalCitedLength;
  bezel_type: CitedBezelType | null;
  case_material: CitedCaseMaterial | null;
  case_colour: CitedColourName | null;
  dial_colour: CitedColourName | null;
  strap_type: CitedStrapType | null;
  crown_position: CitedCrownPosition | null;
  /**
   * Every source this entry cites, the main one first
   *
   * @minItems 1
   */
  sources: [Source, ...Source[]];
}
export interface CitedShape {
  /**
   * The case outline seen from above. 'square' covers rectangular cases too
   */
  value: "round" | "cushion" | "tonneau" | "square" | "other";
  /**
   * A source's ID in the catalogue's source list (S0001, S0002, ...)
   */
  source: string;
}
export interface CitedLength {
  /**
   * A length in millimetres
   */
  value_mm: number;
  /**
   * How far the true value may be from value_mm, from the precision the source gives it with
   */
  tolerance_mm: number;
  /**
   * A source's ID in the catalogue's source list (S0001, S0002, ...)
   */
  source: string;
}
export interface CitedBezelType {
  /**
   * The ring around the crystal
   */
  value: "none" | "smooth" | "fluted" | "rotating_insert" | "other";
  /**
   * A source's ID in the catalogue's source list (S0001, S0002, ...)
   */
  source: string;
}
export interface CitedCaseMaterial {
  /**
   * What the case is made of; gold covers yellow, rose and white gold, told apart by colour
   */
  value:
    "steel" | "titanium" | "gold" | "ceramic" | "resin" | "bronze" | "other";
  /**
   * A source's ID in the catalogue's source list (S0001, S0002, ...)
   */
  source: string;
}
export interface CitedColourName {
  /**
   * A colour as a source or a person names it
   */
  value:
    | "black"
    | "white"
    | "silver"
    | "grey"
    | "blue"
    | "green"
    | "red"
    | "brown"
    | "gold"
    | "champagne"
    | "cream"
    | "orange"
    | "yellow"
    | "pink"
    | "purple"
    | "other";
  /**
   * A source's ID in the catalogue's source list (S0001, S0002, ...)
   */
  source: string;
}
export interface CitedStrapType {
  /**
   * What the watch is worn on
   */
  value: "bracelet" | "leather" | "rubber" | "fabric" | "other";
  /**
   * A source's ID in the catalogue's source list (S0001, S0002, ...)
   */
  source: string;
}
export interface CitedCrownPosition {
  /**
   * Where the crown sits, as an hour on the dial (3 for most watches, 9 for a left-hand crown)
   */
  value: number;
  /**
   * A source's ID in the catalogue's source list (S0001, S0002, ...)
   */
  source: string;
}
export interface Source {
  /**
   * A source's ID in the catalogue's source list (S0001, S0002, ...)
   */
  id: string;
  /**
   * Who published it. A manufacturer's own page is preferred
   */
  kind: "manufacturer" | "retailer" | "review" | "press" | "other";
  publisher: string;
  title: string;
  url: string;
  /**
   * When the page was read
   */
  accessed: string;
  /**
   * A web archive copy, so the citation survives the page changing
   */
  archived_url: string | null;
}
