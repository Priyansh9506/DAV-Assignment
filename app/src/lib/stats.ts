/** Small, dependency-free statistics helpers shared by server and client code. */

/** Quantile with linear interpolation between order statistics (numpy / pandas default). */
export function quantile(sorted: number[], q: number): number {
  if (sorted.length === 0) return NaN
  const pos = (sorted.length - 1) * q
  const lo = Math.floor(pos)
  const hi = Math.ceil(pos)
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo)
}

export function median(values: number[]): number {
  return quantile([...values].sort((a, b) => a - b), 0.5)
}

export type FiveNumber = {
  n: number
  min: number
  q1: number
  median: number
  q3: number
  max: number
  /** Tukey whiskers: the most extreme values inside 1.5 × IQR of the quartiles. */
  whiskerLow: number
  whiskerHigh: number
  outliers: number[]
}

export function fiveNumber(values: number[]): FiveNumber | null {
  if (values.length === 0) return null
  const s = [...values].sort((a, b) => a - b)
  const q1 = quantile(s, 0.25)
  const q3 = quantile(s, 0.75)
  const lowFence = q1 - 1.5 * (q3 - q1)
  const highFence = q3 + 1.5 * (q3 - q1)
  const inside = s.filter((v) => v >= lowFence && v <= highFence)
  return {
    n: s.length,
    min: s[0],
    q1,
    median: quantile(s, 0.5),
    q3,
    max: s[s.length - 1],
    whiskerLow: inside[0],
    whiskerHigh: inside[inside.length - 1],
    outliers: s.filter((v) => v < lowFence || v > highFence),
  }
}

/** Mid-rank percentile: the share of values below `value`, counting ties as half (0-100). */
export function percentileRank(values: number[], value: number): number {
  if (values.length === 0) return NaN
  let below = 0
  let equal = 0
  for (const v of values) {
    if (v < value) below++
    else if (v === value) equal++
  }
  return ((below + equal / 2) / values.length) * 100
}

/** Counts per bin for fixed-width bins [start, start + width), the last bin closed on the right. */
export function histogram(values: number[], start: number, width: number, nBins: number): number[] {
  const counts = new Array<number>(nBins).fill(0)
  for (const v of values) {
    const i = Math.min(Math.floor((v - start) / width), nBins - 1)
    if (i >= 0) counts[i]++
  }
  return counts
}
