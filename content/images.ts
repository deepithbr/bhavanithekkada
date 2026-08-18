/**
 * The image library. Same pattern as `bhavani.ts`: data in JSON, types here.
 *
 * Every asset was extracted from the client-supplied PDFs, deduplicated,
 * de-rotated, cropped and re-encoded to WebP at several widths. Nothing is
 * hotlinked and no stand-in athlete appears anywhere.
 *
 * Rights are unconfirmed across the whole set. See `meta.rightsWarning`.
 */

import raw from "./images.json";

export type ImageCategory =
  | "race"
  | "training"
  | "mountain"
  | "india"
  | "international";

export type RightsStatus = "unconfirmed" | "unconfirmed-agency-derived" | "cleared";

export interface ImageAsset {
  /** Stable key referenced from bhavani.json. */
  slot: string;
  /** Basename. Files are `${file}-${width}.webp` under `meta.basePath`. */
  file: string;
  widths: number[];
  natural: [number, number];
  ratio: number;
  /** Describes the picture. Never repeats the surrounding copy. */
  alt: string;
  credit: string;
  year: string | null;
  location: string | null;
  category: ImageCategory;
  /** [x, y] as fractions, for object-position so crops keep the subject. */
  focal: [number, number];
  rights: RightsStatus;
  note?: string;
}

export interface ImageLibrary {
  meta: {
    lastReviewed: string;
    basePath: string;
    format: string;
    provenance: string;
    rightsWarning: string;
    focalPointNote: string;
  };
  images: ImageAsset[];
  excluded: { source: string; reason: string }[];
}

const library = raw as unknown as ImageLibrary;

export default library;
export const { meta, images, excluded } = library;

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const bySlot = new Map(images.map((i) => [i.slot, i]));

export const image = (slot: string): ImageAsset | undefined => bySlot.get(slot);

export const src = (a: ImageAsset, width?: number): string => {
  const w = width ?? a.widths[a.widths.length - 1];
  return `${meta.basePath}/${a.file}-${w}.webp`;
};

export const srcSet = (a: ImageAsset): string =>
  a.widths.map((w) => `${meta.basePath}/${a.file}-${w}.webp ${w}w`).join(", ");

export const objectPosition = (a: ImageAsset): string =>
  `${(a.focal[0] * 100).toFixed(1)}% ${(a.focal[1] * 100).toFixed(1)}%`;

export const byCategory = (c: ImageCategory): ImageAsset[] =>
  images.filter((i) => i.category === c);

/** Assets that must be replaced or licensed before the site goes public. */
export const needsRightsClearance = (): ImageAsset[] =>
  images.filter((i) => i.rights !== "cleared");
