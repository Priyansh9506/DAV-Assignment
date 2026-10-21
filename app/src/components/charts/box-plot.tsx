"use client"

import * as React from "react"

import { fiveNumber, type FiveNumber } from "@/lib/stats"
import { GROUP_COLOR, GROUP_ORDER } from "@/lib/steel"
import type { GradeRow, GroupName } from "@/lib/types"

const W = 640
const ROW = 40
const LEFT = 136
const RIGHT = 16
const TOP = 8
const AXIS = 28
const MAX = 2500

/** Horizontal Tukey box plots of tensile strength per family group, drawn in SVG (Recharts has no box plot). */
export function StrengthBoxPlot({ rows, groups }: { rows: GradeRow[]; groups: GroupName[] }) {
  const [hover, setHover] = React.useState<GroupName | null>(null)
  const stats = GROUP_ORDER.filter((g) => groups.includes(g)).flatMap((g) => {
    const f = fiveNumber(rows.flatMap((r) => (r.group === g && r.ts != null ? [r.ts] : [])))
    return f ? [{ group: g, f }] : []
  })
  const height = TOP + stats.length * ROW + AXIS
  const x = (v: number) => LEFT + (v / MAX) * (W - LEFT - RIGHT)
  const ticks = [0, 500, 1000, 1500, 2000, 2500]
  const active = stats.find((s) => s.group === hover)

  if (stats.length === 0) return <p className="py-10 text-center text-sm text-muted-foreground">No grades match the filters.</p>

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${height}`} className="w-full" role="img" aria-label="Box plots of tensile strength by family group">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={TOP} y2={height - AXIS} className="stroke-border" />
            <text x={x(t)} y={height - 10} textAnchor="middle" className="fill-muted-foreground text-[11px]">
              {t}
            </text>
          </g>
        ))}
        {stats.map(({ group, f }, i) => {
          const cy = TOP + i * ROW + ROW / 2
          const color = GROUP_COLOR[group]
          const dim = hover && hover !== group
          return (
            <g
              key={group}
              opacity={dim ? 0.35 : 1}
              onMouseEnter={() => setHover(group)}
              onMouseLeave={() => setHover(null)}
              className="cursor-default"
            >
              <rect x={0} y={cy - ROW / 2} width={W} height={ROW} fill="transparent" />
              <text x={LEFT - 10} y={cy + 4} textAnchor="end" className="fill-foreground text-[12px]">
                {group}
              </text>
              <line x1={x(f.whiskerLow)} x2={x(f.whiskerHigh)} y1={cy} y2={cy} stroke={color} strokeWidth={2} />
              <rect
                x={x(f.q1)}
                y={cy - 11}
                width={Math.max(x(f.q3) - x(f.q1), 2)}
                height={22}
                rx={4}
                fill={color}
                fillOpacity={0.28}
                stroke={color}
                strokeWidth={2}
              />
              <line x1={x(f.median)} x2={x(f.median)} y1={cy - 11} y2={cy + 11} className="stroke-foreground" strokeWidth={2.5} />
              {f.outliers.map((o, k) => (
                <circle key={k} cx={x(o)} cy={cy} r={3} fill="none" stroke={color} strokeWidth={1.5} />
              ))}
            </g>
          )
        })}
        <text x={W - RIGHT} y={height - 10} textAnchor="end" className="fill-muted-foreground text-[11px]">
          MPa
        </text>
      </svg>
      {active && <BoxTooltip group={active.group} f={active.f} />}
    </div>
  )
}

function BoxTooltip({ group, f }: { group: GroupName; f: FiveNumber }) {
  const items: [string, number][] = [
    ["Min", f.min],
    ["Q1", f.q1],
    ["Median", f.median],
    ["Q3", f.q3],
    ["Max", f.max],
  ]
  return (
    <div className="pointer-events-none absolute right-2 top-2 rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <div className="mb-1 flex items-center gap-2 font-medium">
        <span className="size-2.5 rounded-full" style={{ background: GROUP_COLOR[group] }} />
        {group} · n = {f.n}
      </div>
      <div className="grid grid-cols-5 gap-3 tabular-nums">
        {items.map(([k, v]) => (
          <div key={k}>
            <div className="text-muted-foreground">{k}</div>
            <div>{Math.round(v)}</div>
          </div>
        ))}
      </div>
      <div className="mt-1 text-muted-foreground">{f.outliers.length} outliers beyond 1.5 × IQR</div>
    </div>
  )
}
