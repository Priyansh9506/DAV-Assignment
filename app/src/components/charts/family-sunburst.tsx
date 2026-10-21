"use client"

import { HoverCard, useHover } from "@/components/charts/chart-tooltip"
import { GROUP_COLOR, GROUP_ORDER } from "@/lib/steel"
import type { GradeRow, GroupName } from "@/lib/types"

const SIZE = 340
const C = SIZE / 2
const R0 = 62 // hole
const R1 = 112 // inner ring (groups)
const R2 = 162 // outer ring (families)
const GAP = 0.004 // radians between slices

function arcPath(a0: number, a1: number, r0: number, r1: number) {
  const large = a1 - a0 > Math.PI ? 1 : 0
  // rounded so server and browser render identical paths
  const p = (r: number, a: number) => `${Math.round((C + r * Math.sin(a)) * 100) / 100},${Math.round((C - r * Math.cos(a)) * 100) / 100}`
  return `M${p(r1, a0)} A${r1},${r1} 0 ${large} 1 ${p(r1, a1)} L${p(r0, a1)} A${r0},${r0} 0 ${large} 0 ${p(r0, a0)} Z`
}

/** Two-ring sunburst: inner ring = family group, outer ring = family; angle = number of grades. */
export function FamilySunburst({ rows }: { rows: GradeRow[] }) {
  const { ref, hover, show, hide } = useHover()
  const total = rows.length
  if (total === 0) return <p className="py-16 text-center text-sm text-muted-foreground">No grades match the filters.</p>

  const groups = GROUP_ORDER.map((g) => {
    const members = rows.filter((r) => r.group === g)
    const fams = Object.entries(
      members.reduce<Record<string, number>>((acc, r) => ((acc[r.familyLabel] = (acc[r.familyLabel] ?? 0) + 1), acc), {}),
    ).sort((a, b) => b[1] - a[1])
    return { group: g, n: members.length, fams }
  }).filter((g) => g.n > 0)

  const slices: { key: string; a0: number; a1: number; r0: number; r1: number; group: GroupName; label: string; n: number; outer: boolean }[] = []
  let a = 0
  for (const g of groups) {
    const span = (g.n / total) * 2 * Math.PI
    slices.push({ key: g.group, a0: a, a1: a + span, r0: R0, r1: R1, group: g.group, label: g.group, n: g.n, outer: false })
    let b = a
    for (const [fam, n] of g.fams) {
      const s = (n / total) * 2 * Math.PI
      slices.push({ key: `${g.group}/${fam}`, a0: b, a1: b + s, r0: R1 + 2, r1: R2, group: g.group, label: fam, n, outer: true })
      b += s
    }
    a += span
  }

  return (
    <div className="grid items-center gap-4 sm:grid-cols-[minmax(0,1fr)_200px] lg:grid-cols-1 xl:grid-cols-[minmax(0,1fr)_190px]">
    <div ref={ref} className="relative mx-auto w-full max-w-[340px]">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="w-full" role="img" aria-label="Sunburst of family groups and families">
        {slices.map((s) => (
          <path
            key={s.key}
            d={arcPath(s.a0 + GAP, Math.max(s.a1 - GAP, s.a0 + GAP * 2), s.r0, s.r1)}
            fill={GROUP_COLOR[s.group]}
            fillOpacity={s.outer ? 0.55 : 0.95}
            stroke="var(--card)"
            strokeWidth={1.5}
            className="cursor-default transition-opacity hover:opacity-80"
            onMouseMove={(e) =>
              show(e, {
                title: s.label,
                color: GROUP_COLOR[s.group],
                lines: [s.outer ? `${s.group}` : "family group", `${s.n} grades · ${((s.n / total) * 100).toFixed(1)} %`],
              })
            }
            onMouseLeave={hide}
          />
        ))}
        <text x={C} y={C - 4} textAnchor="middle" className="fill-foreground text-[22px] font-semibold tabular-nums">
          {total.toLocaleString("en-US")}
        </text>
        <text x={C} y={C + 16} textAnchor="middle" className="fill-muted-foreground text-[11px]">
          grades
        </text>
      </svg>
      <HoverCard hover={hover} />
    </div>
      <ul className="space-y-1.5 text-sm">
        {groups.map((g) => (
          <li key={g.group} className="flex items-center gap-2">
            <span className="size-2.5 shrink-0 rounded-full" style={{ background: GROUP_COLOR[g.group] }} />
            <span className="truncate">{g.group}</span>
            <span className="ml-auto tabular-nums">{g.n}</span>
            <span className="w-11 text-right text-xs tabular-nums text-muted-foreground">{((g.n / total) * 100).toFixed(1)}%</span>
          </li>
        ))}
        <li className="pt-1 text-xs text-muted-foreground">Inner ring: group · outer ring: family. Hover a slice.</li>
      </ul>
    </div>
  )
}
