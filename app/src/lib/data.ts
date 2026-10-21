import "server-only"

import gradesJson from "@/data/grades.json"
import metaJson from "@/data/meta.json"

import { fiveNumber, median, percentileRank, type FiveNumber } from "./stats"
import { GROUP_ORDER, RADAR_ELEMENTS } from "./steel"
import type { Grade, GradeRow, GroupName, Meta } from "./types"

// The full records stay on the server; pages pass only the fields each view needs to the browser.
const grades = gradesJson as unknown as Grade[]
const byId = new Map(grades.map((g) => [g.id, g]))

export const meta = metaJson as unknown as Meta

export function allGrades(): Grade[] {
  return grades
}

export function getGrade(id: string): Grade | undefined {
  return byId.get(id)
}

export function gradeRows(): GradeRow[] {
  return grades.map(
    ({ id, name, group, familyLabel, form, standard, ts, strengthClass, liquidus, liquidusDefault, ce, alloyTotal }) => ({
      id, name, group, familyLabel, form, standard, ts, strengthClass, liquidus, liquidusDefault, ce, alloyTotal,
    }),
  )
}

export type GroupSummary = { group: GroupName; n: number; ts: FiveNumber | null }

export function groupSummaries(): GroupSummary[] {
  return GROUP_ORDER.map((group) => {
    const members = grades.filter((g) => g.group === group)
    return { group, n: members.length, ts: fiveNumber(members.flatMap((g) => (g.ts == null ? [] : [g.ts]))) }
  })
}

export type Standing = { metric: string; value: number; unit: string; inFamily: number; inAll: number; familyMedian: number }

/** Where a grade sits within its own family and within all grades, for the inspector's percentile bars. */
export function standings(grade: Grade): Standing[] {
  const family = grades.filter((g) => g.family === grade.family)
  const metrics: { metric: string; unit: string; get: (g: Grade) => number | null; skip?: (g: Grade) => boolean }[] = [
    { metric: "Tensile strength", unit: "MPa", get: (g) => g.ts },
    { metric: "Carbon equivalent", unit: "", get: (g) => g.ce },
    { metric: "Alloying total", unit: "wt%", get: (g) => g.alloyTotal },
    // The 1460 °C placeholder is not a measurement, so it is left out of the liquidus comparison.
    { metric: "Liquidus", unit: "°C", get: (g) => g.liquidus, skip: (g) => g.liquidusDefault },
  ]
  return metrics.flatMap(({ metric, unit, get, skip }) => {
    const value = get(grade)
    if (value == null || skip?.(grade)) return []
    const pool = (list: Grade[]) => list.flatMap((g) => (skip?.(g) ? [] : get(g) ?? [])) as number[]
    const fam = pool(family)
    return [{
      metric, value, unit,
      inFamily: percentileRank(fam, value),
      inAll: percentileRank(pool(grades), value),
      familyMedian: median(fam),
    }]
  })
}

export type RadarPoint = { element: string; grade: number; group: number }

/**
 * Composition radar: each axis is the percentile of the element among all 1,389 grades (0-100), so trace-level
 * and alloy-level elements share one scale. The second series is the median percentile of the grade's group.
 */
export function compositionRadar(grade: Grade): RadarPoint[] {
  const { byGrade, groupMedian } = radarTables()
  return RADAR_ELEMENTS.map((el, k) => ({
    element: el,
    grade: byGrade.get(grade.id)![k],
    group: groupMedian.get(grade.group)![k],
  }))
}

let radarCache: { byGrade: Map<string, number[]>; groupMedian: Map<GroupName, number[]> } | null = null

// Computed once per server process: every grade's element percentiles and each group's median of them.
function radarTables() {
  if (radarCache) return radarCache
  const perElement = RADAR_ELEMENTS.map((el) => {
    const all = grades.map((g) => g.comp[el] ?? 0)
    return grades.map((g) => percentileRank(all, g.comp[el] ?? 0))
  })
  const byGrade = new Map(grades.map((g, i) => [g.id, perElement.map((col) => col[i])]))
  const groupMedian = new Map(
    GROUP_ORDER.map((group) => {
      const idx = grades.flatMap((g, i) => (g.group === group ? [i] : []))
      return [group, perElement.map((col) => median(idx.map((i) => col[i])))]
    }),
  )
  radarCache = { byGrade, groupMedian }
  return radarCache
}
