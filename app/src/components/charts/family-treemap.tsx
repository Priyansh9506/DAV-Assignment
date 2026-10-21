"use client"

import { Treemap } from "recharts"

import { HoverCard, useHover } from "@/components/charts/chart-tooltip"
import { median } from "@/lib/stats"
import { GROUP_COLOR } from "@/lib/steel"
import type { GradeRow, GroupName } from "@/lib/types"

type Leaf = { name: string; size: number; group: GroupName; medianTs: number | null }

/** Treemap of families: tile area = number of grades, colour = family group, label = median strength. */
export function FamilyTreemap({ rows }: { rows: GradeRow[] }) {
  const { ref, hover, show, hide } = useHover()
  const byFamily = new Map<string, GradeRow[]>()
  for (const r of rows) byFamily.set(r.familyLabel, [...(byFamily.get(r.familyLabel) ?? []), r])
  const data: Leaf[] = [...byFamily.entries()]
    .map(([name, members]) => {
      const ts = members.flatMap((m) => (m.ts == null ? [] : [m.ts]))
      return { name, size: members.length, group: members[0].group, medianTs: ts.length ? median(ts) : null }
    })
    .sort((a, b) => b.size - a.size)

  if (data.length === 0) return <p className="py-16 text-center text-sm text-muted-foreground">No grades match the filters.</p>

  return (
    <div ref={ref} className="relative h-[340px] w-full">
      <Treemap
        data={data}
        dataKey="size"
        nameKey="name"
        aspectRatio={4 / 3}
        isAnimationActive={false}
        width="100%"
        height="100%"
        content={(props: { x: number; y: number; width: number; height: number; depth: number; name?: string; size?: number; group?: GroupName; medianTs?: number | null }) => {
          const { x, y, width, height, depth, name, size, group, medianTs } = props
          if (depth !== 1 || !group) return <g />
          const roomy = width > 70 && height > 34
          return (
            <g
              onMouseMove={(e) =>
                show(e, {
                  title: name ?? "",
                  color: GROUP_COLOR[group],
                  lines: [group, `${size} grades`, medianTs == null ? "no measured strength" : `median ${Math.round(medianTs)} MPa`],
                })
              }
              onMouseLeave={hide}
            >
              <rect x={x} y={y} width={width} height={height} rx={4} fill={GROUP_COLOR[group]} fillOpacity={0.85} stroke="var(--card)" strokeWidth={2} />
              {roomy && (
                <>
                  <text x={x + 8} y={y + 18} className="fill-white text-[12px] font-medium" style={{ paintOrder: "stroke" }}>
                    {name && name.length * 7 > width - 12 ? `${name.slice(0, Math.max(3, Math.floor((width - 16) / 7)))}…` : name}
                  </text>
                  <text x={x + 8} y={y + 33} className="fill-white/85 text-[11px] tabular-nums">
                    {size} · {medianTs == null ? "n/a" : `${Math.round(medianTs)} MPa`}
                  </text>
                </>
              )}
            </g>
          )
        }}
      />
      <HoverCard hover={hover} />
    </div>
  )
}
