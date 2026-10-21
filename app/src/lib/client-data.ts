"use client"

import * as React from "react"

import type { GradePoint, GroupName } from "./types"

// Lists every page can need are served as two static JSON files (written by scripts/build_data.py) instead of being
// embedded in each of the 2,778 prerendered pages. Each file is fetched at most once per visit.

export type SearchItem = { id: string; name: string; group: GroupName }

let searchPromise: Promise<SearchItem[]> | null = null
let pointsPromise: Promise<GradePoint[]> | null = null

export function loadSearchIndex(): Promise<SearchItem[]> {
  searchPromise ??= fetch("/data/search.json")
    .then((r) => r.json() as Promise<[string, string, GroupName][]>)
    .then((rows) => rows.map(([id, name, group]) => ({ id, name, group })))
  return searchPromise
}

export function loadPoints(): Promise<GradePoint[]> {
  pointsPromise ??= Promise.all([
    loadSearchIndex(),
    fetch("/data/points.json").then((r) => r.json() as Promise<[string, number, number][]>),
  ]).then(([items, rows]) => {
    const byId = new Map(items.map((i) => [i.id, i]))
    return rows.map(([id, x, y]) => ({ id, name: byId.get(id)!.name, group: byId.get(id)!.group, pc: [x, y] }))
  })
  return pointsPromise
}

/** Resolves `loader` once `enabled` is true; returns null until the data has arrived. */
export function useLoaded<T>(loader: () => Promise<T>, enabled = true): T | null {
  const [value, setValue] = React.useState<T | null>(null)
  React.useEffect(() => {
    if (!enabled || value) return
    let live = true
    loader().then((v) => live && setValue(v))
    return () => {
      live = false
    }
  }, [enabled, loader, value])
  return value
}
