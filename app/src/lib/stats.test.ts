import { describe, expect, it } from "vitest"

import { fiveNumber, histogram, median, percentileRank, quantile } from "./stats"

describe("quantile", () => {
  it("interpolates linearly like numpy", () => {
    const s = [1, 2, 3, 4]
    expect(quantile(s, 0.25)).toBeCloseTo(1.75)
    expect(quantile(s, 0.5)).toBeCloseTo(2.5)
    expect(quantile(s, 1)).toBe(4)
  })
  it("returns NaN for no data", () => {
    expect(quantile([], 0.5)).toBeNaN()
  })
})

describe("fiveNumber", () => {
  it("finds Tukey whiskers and outliers", () => {
    const f = fiveNumber([1, 2, 3, 4, 5, 6, 7, 8, 100])!
    expect(f.median).toBe(5)
    expect(f.q1).toBe(3)
    expect(f.q3).toBe(7)
    expect(f.whiskerHigh).toBe(8)
    expect(f.outliers).toEqual([100])
  })
  it("does not mutate its input", () => {
    const v = [3, 1, 2]
    fiveNumber(v)
    expect(v).toEqual([3, 1, 2])
  })
})

describe("percentileRank", () => {
  it("counts ties as half", () => {
    expect(percentileRank([1, 2, 2, 3], 2)).toBe(50)
    expect(percentileRank([1, 2, 3, 4], 0)).toBe(0)
    expect(percentileRank([1, 2, 3, 4], 9)).toBe(100)
  })
})

describe("histogram", () => {
  it("closes the last bin on the right", () => {
    expect(histogram([0, 5, 10, 19.9, 20], 0, 10, 2)).toEqual([2, 3])
  })
  it("matches median for odd counts", () => {
    expect(median([5, 1, 3])).toBe(3)
  })
})
