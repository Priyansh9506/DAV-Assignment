export type GroupName =
  | "Carbon & low-alloy"
  | "Stainless"
  | "Cast iron"
  | "Tool & high-speed"
  | "Weld metal"
  | "Other"

export type ProductForm = "wrought" | "cast" | "weld"

export type Neighbour = {
  id: string
  /** Euclidean distance in the log1p + z-score composition space (same space as the PCA map). */
  distance: number
  /** Share of all grade pairs that are farther apart than this one (0-1). */
  fartherShare: number
}

/** One canonical grade, as written by scripts/build_data.py. */
export type Grade = {
  id: string
  name: string
  alt: string | null
  family: string
  familyLabel: string
  group: GroupName
  form: ProductForm
  standard: string
  listings: number
  /** Tensile strength in MPa; null for the 7 grades without a measured value. */
  ts: number | null
  strengthClass: number | null
  liquidus: number
  /** True when the liquidus is the dataset's 1460 °C placeholder rather than a grade-specific value. */
  liquidusDefault: boolean
  /** wt% of every element present (> 0). */
  comp: Record<string, number>
  traceTotal: number
  alloyTotal: number
  ce: number
  crEq: number
  niEq: number
  /** Number of other grades with an identical composition (processing variants). */
  chemTwins: number
  pc: [number, number]
  neighbours: Neighbour[]
}

export type Meta = {
  source: string
  nGrades: number
  nMeasured: number
  elements: string[]
  rareElements: string[]
  pcaFeatures: string[]
  groupOrder: GroupName[]
  pca: {
    explained: number[]
    componentsFor80: number
    topLoadings: Record<"PC1" | "PC2", { element: string; loading: number }[]>
  }
  defaultLiquidus: number
  nDefaultLiquidus: number
  cleaning: { step: string; detail: string; rowsAfter: number }[]
  strengthClasses: { value: number; label: string; min: number; max: number }[]
}

/** The slim row the Explorer and Target designer send to the browser. */
export type GradeRow = Pick<
  Grade,
  "id" | "name" | "group" | "familyLabel" | "form" | "standard" | "ts" | "liquidus" | "liquidusDefault" | "ce" | "alloyTotal"
>

/** The slimmest row: grade search and the PCA map. */
export type GradePoint = Pick<Grade, "id" | "name" | "group" | "pc">
