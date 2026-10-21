"use client"

import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart } from "recharts"

import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { GROUP_COLOR } from "@/lib/steel"
import type { GroupName } from "@/lib/types"

type Point = { element: string; grade: number; group: number }

/** The grade's element percentiles (among all grades) against the median of its family group. */
export function CompositionRadar({ data, gradeName, group }: { data: Point[]; gradeName: string; group: GroupName }) {
  const config = {
    grade: { label: gradeName.length > 28 ? `${gradeName.slice(0, 26)}…` : gradeName, color: "var(--foreground)" },
    group: { label: `${group} median`, color: GROUP_COLOR[group] },
  }
  return (
    <ChartContainer config={config} className="mx-auto aspect-square max-h-[320px] w-full">
      <RadarChart data={data} outerRadius="72%">
        <ChartTooltip
          content={<ChartTooltipContent formatter={(v, name) => `${config[name as "grade" | "group"].label}: ${Math.round(Number(v))}th pct`} />}
        />
        <PolarGrid className="stroke-border" />
        <PolarAngleAxis dataKey="element" tick={{ className: "fill-foreground text-[12px]" }} />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        <Radar isAnimationActive={false} dataKey="group" stroke={GROUP_COLOR[group]} fill={GROUP_COLOR[group]} fillOpacity={0.25} strokeWidth={2} />
        <Radar isAnimationActive={false} dataKey="grade" stroke="var(--foreground)" fill="var(--foreground)" fillOpacity={0.08} strokeWidth={2} dot={{ r: 3 }} />
        <ChartLegend itemSorter={null} content={<ChartLegendContent />} />
      </RadarChart>
    </ChartContainer>
  )
}
