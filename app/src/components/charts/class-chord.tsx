"use client"

import { HoverCard, useHover } from "@/components/charts/chart-tooltip"
import { GROUP_COLOR, GROUP_ORDER, STRENGTH_CLASS_LABEL } from "@/lib/steel"
import type { GradeRow, GroupName } from "@/lib/types"

const W = 640
const H = 420
const CX = W / 2
const CY = H / 2
const R = 150
const SPLIT = 0.12 // radians kept empty at the top and bottom between the two halves
const GAP = 0.03 // radians between neighbouring nodes
const CLASS_ORDER = [2, 1, 0]

type Flow = { group: GroupName; cls: number; n: number }

// Rounded so the server-rendered and browser-rendered SVG match exactly (Math.sin can differ in the last digits).
const r2 = (v: number) => Math.round(v * 100) / 100
const pt = (a: number, r = R) => [r2(CX + r * Math.sin(a)), r2(CY - r * Math.cos(a))] as const

/**
 * Chord (circular migration) diagram: family groups on the left, strength classes on the right, ribbon width = number
 * of grades. Same geometry as the notebook / KNIME chord: arcs on a circle joined by cubic Bézier ribbons.
 */
export function ClassChord({ rows }: { rows: GradeRow[] }) {
  const { ref, hover, show, hide } = useHover()
  const measured = rows.filter((r) => r.strengthClass != null)
  const flows: Flow[] = GROUP_ORDER.flatMap((group) =>
    CLASS_ORDER.map((cls) => ({ group, cls, n: measured.filter((r) => r.group === group && r.strengthClass === cls).length })),
  ).filter((f) => f.n > 0)
  const total = flows.reduce((s, f) => s + f.n, 0)
  if (total === 0) return <p className="py-16 text-center text-sm text-muted-foreground">No measured grades match the filters.</p>

  const groups = GROUP_ORDER.filter((g) => flows.some((f) => f.group === g))
  const classes = CLASS_ORDER.filter((c) => flows.some((f) => f.cls === c))
  const per = (k: (f: Flow) => boolean) => flows.filter(k).reduce((s, f) => s + f.n, 0)

  // Left half runs from bottom (π + SPLIT) up to the top (2π − SPLIT); right half from top (SPLIT) down to bottom (π − SPLIT).
  const leftSpan = Math.PI - 2 * SPLIT - GAP * (groups.length - 1)
  const rightSpan = Math.PI - 2 * SPLIT - GAP * (classes.length - 1)
  const gArc = new Map<GroupName, [number, number]>()
  let a = 2 * Math.PI - SPLIT
  for (const g of groups) {
    const s = (per((f) => f.group === g) / total) * leftSpan
    gArc.set(g, [a - s, a])
    a -= s + GAP
  }
  const cArc = new Map<number, [number, number]>()
  a = SPLIT
  for (const c of classes) {
    const s = (per((f) => f.cls === c) / total) * rightSpan
    cArc.set(c, [a, a + s])
    a += s + GAP
  }

  const gCur = new Map([...gArc].map(([k, v]) => [k, v[1]]))
  const cCur = new Map([...cArc].map(([k, v]) => [k, v[0]]))
  const ribbons = flows.map((f) => {
    const gs = (f.n / total) * leftSpan
    const cs = (f.n / total) * rightSpan
    const g1 = gCur.get(f.group)!
    const g0 = g1 - gs
    gCur.set(f.group, g0)
    const c0 = cCur.get(f.cls)!
    const c1 = c0 + cs
    cCur.set(f.cls, c1)
    const [sx0, sy0] = pt(g0)
    const [sx1, sy1] = pt(g1)
    const [tx0, ty0] = pt(c0)
    const [tx1, ty1] = pt(c1)
    const d = [
      `M${sx0},${sy0}`,
      `A${R},${R} 0 0 1 ${sx1},${sy1}`,
      `C${CX},${CY} ${CX},${CY} ${tx0},${ty0}`,
      `A${R},${R} 0 0 1 ${tx1},${ty1}`,
      `C${CX},${CY} ${CX},${CY} ${sx0},${sy0}`,
      "Z",
    ].join(" ")
    return { ...f, d }
  })

  const arc = (a0: number, a1: number, r0: number, r1: number) => {
    const [x0, y0] = pt(a0, r1)
    const [x1, y1] = pt(a1, r1)
    const [x2, y2] = pt(a1, r0)
    const [x3, y3] = pt(a0, r0)
    const large = a1 - a0 > Math.PI ? 1 : 0
    return `M${x0},${y0} A${r1},${r1} 0 ${large} 1 ${x1},${y1} L${x2},${y2} A${r0},${r0} 0 ${large} 0 ${x3},${y3} Z`
  }
  const label = (a0: number, a1: number) => {
    const m = (a0 + a1) / 2
    const [x, y] = pt(m, R + 24)
    return { x, y, anchor: (Math.sin(m) < 0 ? "end" : "start") as "end" | "start" }
  }
  // Small neighbouring arcs would print their labels on top of each other: keep at least 15 px between labels on a side.
  const spread = <K,>(entries: [K, [number, number]][]) => {
    const ls = entries.map(([k, [a0, a1]]) => ({ k, ...label(a0, a1) })).sort((p, q) => p.y - q.y)
    for (let i = 1; i < ls.length; i++) ls[i].y = Math.max(ls[i].y, ls[i - 1].y + 15)
    for (let i = ls.length - 1; i > 0; i--) {
      if (ls[i].y > H - 8) ls[i].y = H - 8
      ls[i - 1].y = Math.min(ls[i - 1].y, ls[i].y - 15)
    }
    return new Map(ls.map((l) => [l.k, l]))
  }
  const gLabel = spread([...gArc])
  const cLabel = spread([...cArc])

  return (
    <div ref={ref} className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Chord diagram of family groups and strength classes">
        {ribbons.map((r) => (
          <path
            key={`${r.group}-${r.cls}`}
            d={r.d}
            fill={GROUP_COLOR[r.group]}
            fillOpacity={0.45}
            stroke={GROUP_COLOR[r.group]}
            strokeOpacity={0.6}
            strokeWidth={0.5}
            className="hover:[fill-opacity:0.8]"
            onMouseMove={(e) =>
              show(e, {
                title: `${r.group} → ${STRENGTH_CLASS_LABEL[r.cls]}`,
                color: GROUP_COLOR[r.group],
                lines: [
                  `${r.n} grades`,
                  `${((r.n / per((f) => f.group === r.group)) * 100).toFixed(0)} % of ${r.group.toLowerCase()}`,
                ],
              })
            }
            onMouseLeave={hide}
          />
        ))}
        {[...gArc].map(([g, [a0, a1]]) => {
          const l = gLabel.get(g)!
          return (
            <g key={g}>
              <path d={arc(a0, a1, R + 2, R + 14)} fill={GROUP_COLOR[g]} />
              <text x={l.x} y={l.y} textAnchor={l.anchor} dominantBaseline="middle" className="fill-foreground text-[12px]">
                {g} <tspan className="fill-muted-foreground tabular-nums">{per((f) => f.group === g)}</tspan>
              </text>
            </g>
          )
        })}
        {[...cArc].map(([c, [a0, a1]]) => {
          const l = cLabel.get(c)!
          return (
            <g key={c}>
              <path d={arc(a0, a1, R + 2, R + 14)} className="fill-muted-foreground" />
              <text x={l.x} y={l.y} textAnchor={l.anchor} dominantBaseline="middle" className="fill-foreground text-[12px]">
                {STRENGTH_CLASS_LABEL[c]} <tspan className="fill-muted-foreground tabular-nums">{per((f) => f.cls === c)}</tspan>
              </text>
            </g>
          )
        })}
      </svg>
      <HoverCard hover={hover} />
    </div>
  )
}
