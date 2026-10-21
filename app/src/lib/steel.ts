import type { GroupName, ProductForm } from "./types"

export const GROUP_ORDER: GroupName[] = [
  "Carbon & low-alloy",
  "Stainless",
  "Cast iron",
  "Tool & high-speed",
  "Weld metal",
  "Other",
]

/**
 * Family-group colours as CSS variables (defined per theme in globals.css). The palette passes the dataviz checks in
 * both modes on the default adjacent pairs; in light mode three hues sit below 3:1 on white, so every chart also shows
 * labels, a legend or a table. Scatter plots add a shape per group for colour-blind readers.
 */
export const GROUP_COLOR: Record<GroupName, string> = {
  "Carbon & low-alloy": "var(--group-carbon)",
  Stainless: "var(--group-stainless)",
  "Cast iron": "var(--group-cast-iron)",
  "Tool & high-speed": "var(--group-tool)",
  "Weld metal": "var(--group-weld)",
  Other: "var(--group-other)",
}

export const GROUP_SHAPE: Record<GroupName, "circle" | "diamond" | "triangle" | "square" | "cross" | "star"> = {
  "Carbon & low-alloy": "circle",
  Stainless: "diamond",
  "Cast iron": "triangle",
  "Tool & high-speed": "square",
  "Weld metal": "cross",
  Other: "star",
}

export const GROUP_BLURB: Record<GroupName, string> = {
  "Carbon & low-alloy": "Plain carbon, alloy, boron, bearing, spring, nitriding and weathering steels",
  Stainless: "Chromium-rich, corrosion-resistant grades",
  "Cast iron": "Grey, ductile, malleable and austenitic (Ni-Resist) irons",
  "Tool & high-speed": "Tool and high-speed steels rich in W, V, Mo and Co carbide formers",
  "Weld metal": "AWS filler and electrode deposits",
  Other: "Maraging steels and Fe-Ni/Co special alloys",
}

export const FORM_LABEL: Record<ProductForm, string> = { wrought: "Wrought", cast: "Cast", weld: "Weld metal" }

/** Strength classes as rebuilt in notebook 01 (edges 300 and 600 MPa). */
export const STRENGTH_CLASS_LABEL: Record<number, string> = {
  0: "Low (< 300 MPa)",
  1: "Medium (300-600 MPa)",
  2: "High (> 600 MPa)",
}

export const ELEMENT_NAME: Record<string, string> = {
  Al: "Aluminium", As: "Arsenic", B: "Boron", C: "Carbon", Ca: "Calcium", Ce: "Cerium", Co: "Cobalt",
  Cr: "Chromium", Cu: "Copper", Fe: "Iron", La: "Lanthanum", Mg: "Magnesium", Mn: "Manganese",
  Mo: "Molybdenum", N: "Nitrogen", Nb: "Niobium", Ni: "Nickel", O: "Oxygen", P: "Phosphorus", Pb: "Lead",
  S: "Sulphur", Se: "Selenium", Si: "Silicon", Sn: "Tin", Ta: "Tantalum", Ti: "Titanium", V: "Vanadium",
  W: "Tungsten", Zn: "Zinc", Zr: "Zirconium",
}

/** Elements shown on the composition radar: the ones that define the six family groups. */
export const RADAR_ELEMENTS = ["C", "Mn", "Si", "Cr", "Ni", "Mo", "V", "W", "Co", "Cu"]

export type CeBand = { label: string; tone: "good" | "warning" | "critical"; advice: string }

/** IIW carbon-equivalent weldability bands. Only meaningful for carbon and low-alloy steels. */
export function ceBand(ce: number): CeBand {
  if (ce <= 0.4) return { label: "Readily weldable", tone: "good", advice: "CE ≤ 0.40: no preheat normally needed." }
  if (ce <= 0.6) return { label: "Preheat advised", tone: "warning", advice: "0.40 < CE ≤ 0.60: preheat and control hydrogen." }
  return { label: "Difficult to weld", tone: "critical", advice: "CE > 0.60: high cracking risk, needs a qualified procedure." }
}

/** The terms of the IIW carbon equivalent, CE = C + Mn/6 + (Cr + Mo + V)/5 + (Ni + Cu)/15, in display order. */
export function ceTerms(comp: Record<string, number>): { label: string; value: number }[] {
  const el = (s: string) => comp[s] ?? 0
  return [
    { label: "C", value: el("C") },
    { label: "Mn / 6", value: el("Mn") / 6 },
    { label: "Cr / 5", value: el("Cr") / 5 },
    { label: "Mo / 5", value: el("Mo") / 5 },
    { label: "V / 5", value: el("V") / 5 },
    { label: "Ni / 15", value: el("Ni") / 15 },
    { label: "Cu / 15", value: el("Cu") / 15 },
  ]
}

export const fmt = {
  mpa: (v: number | null) => (v == null ? "n/a" : `${Math.round(v).toLocaleString("en-US")} MPa`),
  pct: (v: number, digits = 0) => `${v.toFixed(digits)} %`,
  wt: (v: number) => (v >= 10 ? v.toFixed(1) : v >= 1 ? v.toFixed(2) : v >= 0.01 ? v.toFixed(3) : v.toPrecision(2)),
  num: (v: number, digits = 2) => v.toFixed(digits),
}

/** SAE-AISI 4140, the Cr-Mo workhorse used as the example grade across the notebooks and guides. */
export const FEATURED_GRADE_ID = "G1092"

/** CSS-safe keys for chart configs (group names contain spaces and "&"). */
export const GROUP_KEY: Record<GroupName, string> = {
  "Carbon & low-alloy": "carbon",
  Stainless: "stainless",
  "Cast iron": "castIron",
  "Tool & high-speed": "tool",
  "Weld metal": "weld",
  Other: "other",
}

export const GROUP_CHART_CONFIG = Object.fromEntries(
  GROUP_ORDER.map((g) => [GROUP_KEY[g], { label: g, color: GROUP_COLOR[g] }]),
) as Record<string, { label: string; color: string }>
