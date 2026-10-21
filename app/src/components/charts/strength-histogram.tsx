"use client"

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"

import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { histogram } from "@/lib/stats"
import { GROUP_CHART_CONFIG, GROUP_KEY, GROUP_ORDER } from "@/lib/steel"
import type { GradeRow, GroupName } from "@/lib/types"

const START = 0
const WIDTH = 100
const BINS = 25 // 0 … 2500 MPa covers the full measured range

/** Stacked histogram of tensile strength, one colour per family group. */
export function StrengthHistogram({ rows, groups }: { rows: GradeRow[]; groups: GroupName[] }) {
  const shown = GROUP_ORDER.filter((g) => groups.includes(g))
  const counts = Object.fromEntries(
    shown.map((g) => [
      g,
      histogram(rows.flatMap((r) => (r.group === g && r.ts != null ? [r.ts] : [])), START, WIDTH, BINS),
    ]),
  )
  const data = Array.from({ length: BINS }, (_, i) => ({
    bin: `${START + i * WIDTH}–${START + (i + 1) * WIDTH}`,
    ...Object.fromEntries(shown.map((g) => [GROUP_KEY[g], counts[g][i]])),
  }))

  return (
    <ChartContainer config={GROUP_CHART_CONFIG} className="aspect-auto h-[300px] w-full">
      <BarChart data={data} margin={{ left: 4, right: 8, top: 8 }} barCategoryGap={1}>
        <CartesianGrid vertical={false} strokeDasharray="0" strokeOpacity={0.5} />
        <XAxis
          dataKey="bin"
          tickLine={false}
          axisLine={false}
          interval={4}
          tickFormatter={(v: string) => v.split("–")[0]}
          label={{ value: "Tensile strength (MPa, 100 MPa bins)", position: "insideBottom", offset: -2, className: "fill-muted-foreground text-[11px]" }}
          height={36}
        />
        <YAxis tickLine={false} axisLine={false} width={36} allowDecimals={false} />
        <ChartTooltip cursor={{ fillOpacity: 0.3 }} content={<ChartTooltipContent labelFormatter={(l) => `${l} MPa`} />} />
        <ChartLegend itemSorter={null} content={<ChartLegendContent />} />
        {shown.map((g, i) => (
          <Bar
            key={g}
            dataKey={GROUP_KEY[g]}
            stackId="ts"
            fill={`var(--color-${GROUP_KEY[g]})`}
            stroke="var(--card)"
            strokeWidth={1}
            radius={i === shown.length - 1 ? [3, 3, 0, 0] : 0}
          />
        ))}
      </BarChart>
    </ChartContainer>
  )
}
