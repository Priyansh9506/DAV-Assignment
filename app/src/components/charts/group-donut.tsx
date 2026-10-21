"use client"

import { Cell, Pie, PieChart } from "recharts"

import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { GROUP_CHART_CONFIG, GROUP_COLOR, GROUP_KEY, GROUP_ORDER } from "@/lib/steel"
import type { GradeRow } from "@/lib/types"

/** Donut of grades per family group, with a direct-labelled legend (counts and shares) beside it. */
export function GroupDonut({ rows }: { rows: GradeRow[] }) {
  const data = GROUP_ORDER.map((g) => ({
    key: GROUP_KEY[g],
    group: g,
    count: rows.filter((r) => r.group === g).length,
  })).filter((d) => d.count > 0)
  const total = rows.length

  return (
    <div className="grid items-center gap-4 sm:grid-cols-[180px_1fr]">
      <ChartContainer config={GROUP_CHART_CONFIG} className="mx-auto aspect-square h-[180px]">
        <PieChart>
          <ChartTooltip content={<ChartTooltipContent nameKey="key" hideLabel />} />
          <Pie data={data} dataKey="count" nameKey="key" innerRadius="62%" outerRadius="100%" stroke="var(--card)" strokeWidth={2}>
            {data.map((d) => (
              <Cell key={d.key} fill={GROUP_COLOR[d.group]} />
            ))}
          </Pie>
          <text x="50%" y="47%" textAnchor="middle" className="fill-foreground text-xl font-semibold">
            {total.toLocaleString("en-US")}
          </text>
          <text x="50%" y="60%" textAnchor="middle" className="fill-muted-foreground text-[11px]">
            grades
          </text>
        </PieChart>
      </ChartContainer>
      <ul className="space-y-1.5 text-sm">
        {data.map((d) => (
          <li key={d.key} className="flex items-center gap-2">
            <span className="size-2.5 shrink-0 rounded-full" style={{ background: GROUP_COLOR[d.group] }} />
            <span className="truncate">{d.group}</span>
            <span className="ml-auto tabular-nums">{d.count}</span>
            <span className="w-12 text-right text-xs tabular-nums text-muted-foreground">
              {((d.count / total) * 100).toFixed(1)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
