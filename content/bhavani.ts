/**
 * Single typed entry point for every factual claim on the site.
 *
 * The data itself lives in `bhavani.json` so that three consumers can share one
 * source of truth without any of them duplicating it:
 *
 *   1. `build.py`          reads the JSON and renders static `index.html`
 *   2. `assets/js/data.js` is generated from the JSON for the interactive parts
 *   3. this module         is what a Next.js app would import
 *
 * Nothing factual is written directly into markup. If a claim is not in the
 * JSON it does not appear on the site.
 *
 * On porting to Next.js: `resolveJsonModule` in tsconfig, then this file works
 * unchanged. Delete `build.py` and `assets/js/data.js` at that point.
 */

import raw from "./bhavani.json";

/* ------------------------------------------------------------------ */
/* Provenance                                                          */
/* ------------------------------------------------------------------ */

export type SourceType = "public-primary" | "public-secondary" | "client-supplied";

export interface Source {
  sourceType: SourceType;
  sourceName: string;
  sourceUrl?: string | null;
  verified: boolean;
  needsConfirmation: boolean;
  lastChecked?: string;
  note?: string;
}

/** Key into `sources`. Every factual record carries one. */
export type SourceRef = "fis" | "awg-wikipedia" | "kiwg-2026" | "ap" | "portfolio";

/* ------------------------------------------------------------------ */
/* Records                                                             */
/* ------------------------------------------------------------------ */

export interface Identity {
  fullName: string;
  wordmark: string;
  shortName: string;
  descriptor: string;
  discipline: string;
  nation: string;
  nationCode: string;
  region: string;
  birthDate: string;
  birthPlace: string;
  fisCode: string;
  source: Source;
}

export interface Cta {
  label: string;
  href: string;
}

export interface Hero {
  eyebrow: string;
  line: string;
  standfirst: string;
  standfirstSource: Source;
  ctaPrimary: Cta;
  ctaSecondary: Cta;
  ctaTertiary: Cta;
  image: string;
}

export interface ProofItem {
  id: string;
  label: string;
  detail: string;
  year: string;
  figure: string;
  sourceRef: SourceRef;
}

/** Drives the warm-to-cold gradient down the page. */
export type Temperature = "warm" | "cool" | "cold";

export interface StoryBeat {
  id: string;
  year: string;
  heading: string;
  body: string;
  image: string | null;
  temperature: Temperature;
  sourceRef: SourceRef;
}

export interface Story {
  sectionTitle: string;
  sectionIndex: string;
  beats: StoryBeat[];
}

/** Sets the checkpoint treatment on The Track. */
export type Phase = "origin" | "mountain" | "international" | "worldcup";

export interface Milestone {
  id: string;
  year: string;
  date: string;
  title: string;
  location: string;
  line: string;
  result: string | null;
  image: string | null;
  phase: Phase;
  sourceRef: SourceRef;
}

export interface LatPoint {
  place: string;
  lat: number;
  label: string;
}

export interface SignatureStat {
  headline: string;
  from: LatPoint;
  to: LatPoint;
  origin: LatPoint;
  note: string;
  sourceRef: SourceRef;
}

export type FootprintKind =
  | "origin"
  | "domestic"
  | "fis"
  | "championship"
  | "worldcup"
  | "podium";

export interface FootprintPlace {
  id: string;
  place: string;
  country: string;
  lat: number;
  lon: number;
  years: string[];
  event: string;
  kind: FootprintKind;
  sourceRef: SourceRef;
}

export interface MountainAchievement {
  id: string;
  peak: string;
  country: string;
  metres: number;
  note: string;
  image: string | null;
  sourceRef: SourceRef;
}

export interface Certification {
  id: string;
  title: string;
  body: string;
  year: string | null;
  sourceRef: SourceRef;
}

export type Medal = "gold" | "silver" | "bronze";
export type ResultTag = "international" | "khelo-india" | "national" | "biathlon";

export interface ResultRow {
  id: string;
  year: string | null;
  event: string;
  detail: string;
  place: string;
  medal: Medal | null;
  mark: string | null;
  tags: ResultTag[];
  /** Shown before the record is expanded. */
  featured: boolean;
  sourceRef: SourceRef;
}

export interface Results {
  note: string;
  filters: { id: string; label: string }[];
  rows: ResultRow[];
}

export interface PressItem {
  id: string;
  publication: string;
  title: string;
  date: string | null;
  byline: string | null;
  context: string;
  url: string;
  verified: boolean;
}

export interface PartnershipArea {
  id: string;
  index: string;
  title: string;
  body: string;
}

export interface Partnership {
  heading: string;
  sectionIndex: string;
  standfirst: string;
  standfirstSource: Source;
  areas: PartnershipArea[];
  cta: Cta;
  budgetNote: string;
  /** Deliberately empty. No partner is named until an agreement is confirmed. */
  partners: never[];
}

export interface Contact {
  email: string;
  phone: string;
  phoneHref: string;
  instagramHandle: string;
  instagramUrl: string;
  instagramVerified: boolean;
  formIsPrototype: boolean;
  source: Source;
}

export interface Seo {
  title: string;
  description: string;
  ogImage: string;
  siteUrl: string;
}

/**
 * Claims that exist in the source material and are deliberately not published,
 * or are published only in a weakened form. This array is a deliverable in its
 * own right: it is the record of what was held back and why.
 */
export interface WithheldClaim {
  claim: string;
  origin: string;
  why: string;
  status:
    | "client-supplied-needs-verification"
    | "contradicted-by-source"
    | "partly-verified-figure-published-as-result"
    | "reported-attributed"
    | "removed";
}

export interface BhavaniContent {
  meta: { lastReviewed: string; reviewedBy: string; note: string };
  identity: Identity;
  hero: Hero;
  proofOfLevel: ProofItem[];
  story: Story;
  careerMilestones: Milestone[];
  signatureStat: SignatureStat;
  internationalFootprint: FootprintPlace[];
  mountainAchievements: MountainAchievement[];
  certifications: Certification[];
  results: Results;
  press: PressItem[];
  gallery: { groups: { id: string; label: string }[] };
  partnership: Partnership;
  contact: Contact;
  seo: Seo;
  sources: Record<SourceRef, Source>;
  withheld: WithheldClaim[];
}

const content = raw as unknown as BhavaniContent;

export default content;

export const {
  identity,
  hero,
  proofOfLevel,
  story,
  careerMilestones,
  signatureStat,
  internationalFootprint,
  mountainAchievements,
  certifications,
  results,
  press,
  gallery,
  partnership,
  contact,
  seo,
  sources,
  withheld,
} = content;

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

export const sourceFor = (ref: SourceRef): Source => content.sources[ref];

/** True when a record may be presented without a "to be confirmed" marker. */
export const isPublishable = (ref: SourceRef): boolean => {
  const s = content.sources[ref];
  return s.verified && !s.needsConfirmation;
};

export const featuredResults = (): ResultRow[] =>
  content.results.rows.filter((r) => r.featured);

export const resultsByTag = (tag: ResultTag | "all"): ResultRow[] =>
  tag === "all"
    ? content.results.rows
    : content.results.rows.filter((r) => r.tags.includes(tag));

/**
 * Person schema built only from verified fields. Nothing from `withheld` and
 * nothing sourced to `portfolio` is allowed in here.
 */
export const personSchema = () => ({
  "@context": "https://schema.org",
  "@type": "Person",
  name: content.identity.fullName,
  alternateName: content.identity.shortName,
  birthDate: content.identity.birthDate,
  nationality: { "@type": "Country", name: content.identity.nation },
  jobTitle: "Cross-country skier",
  url: content.seo.siteUrl,
  image: content.seo.ogImage,
  sameAs: [content.sources.fis.sourceUrl].filter(Boolean) as string[],
});
