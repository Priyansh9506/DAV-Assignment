"use client"

import { useRouter } from "next/navigation"
import { CartesianGrid, Scatter, ScatterChart, XAxis, YAxis, ZAxis } from "recharts"

import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip } from "@/components/ui/chart"
import { Skeleton } from "@/components/ui/skeleton"
import { loadPoints, useLoaded } from "@/lib/client-data"
import { GROUP_CHART_CONFIG, GROUP_COLOR, GROUP_KEY, GROUP_ORDER, GROUP_SHAPE } from "@/lib/steel"
import type { GradePoint, GroupName } from "@/lib/types"

type Pt = { x: number; y: number; id: string; name: string; group: GroupName }

/**
 * The PCA chemistry map: every grade as a faint point (colour + shape per group), the selected grade as a large star
 * and its substitutes ringed. Clicking a point opens that grade's substitutes.
 */
export function PcaMap({
  selectedId,
  highlightIds,
  axisLabels,
}: {
  selectedId: string
  highlightIds: string[]
  axisLabels: [string, string]
}) {
  const router = useRouter()
  const points = useLoaded(loadPoints)
  if (!points) return <Skeleton className="h-[440px] w-full" />
  const toPt = (p: GradePoint): Pt => ({ x: p.pc[0], y: p.pc[1], id: p.id, name: p.name, group: p.group })
  const highlight = new Set(highlightIds)
  const selected = points.find((p) => p.id === selectedId)
  const ringed = points.filter((p) => highlight.has(p.id)).map(toPt)

  return (
    <ChartContainer config={GROUP_CHART_CONFIG} className="aspect-auto h-[440px] w-full">
      <ScatterChart margin={{ top: 8, right: 12, bottom: 24, left: 4 }}>
        <CartesianGrid strokeOpacity={0.4} />
        <XAxis type="number" dataKey="x" tickLine={false} axisLine={false} label={{ value: axisLabels[0], position: "insideBottom", offset: -14, className: "fill-muted-foreground text-[11px]" }} />
        <YAxis type="number" dataKey="y" tickLine={false} axisLine={false} width={36} label={{ value: axisLabels[1], angle: -90, position: "insideLeft", className: "fill-muted-foreground text-[11px]" }} />
        <ZAxis range={[22, 22]} />
        <ChartTooltip cursor={false} content={<PointTooltip />} />
        <ChartLegend itemSorter={null} content={<ChartLegendContent />} />
        {GROUP_ORDER.map((g) => (
          <Scatter
            key={g}
            name={GROUP_KEY[g]}
            data={points.filter((p) => p.group === g && !highlight.has(p.id) && p.id !== selectedId).map(toPt)}
            fill={GROUP_COLOR[g]}
            fillOpacity={0.35}
            shape={GROUP_SHAPE[g]}
            isAnimationActive={false}
            onClick={(d: { payload?: Pt }) => d.payload && router.push(`/substitutes/${d.payload.id}`)}
            className="cursor-pointer"
          />
        ))}
        <Scatter
          name="substitutes"
          legendType="none"
          data={ringed}
          isAnimationActive={false}
          shape={(props: { cx?: number; cy?: number; payload?: Pt }) => (
            <g>
              <circle cx={props.cx} cy={props.cy} r={9} fill="none" stroke="var(--foreground)" strokeWidth={2} />
              <circle cx={props.cx} cy={props.cy} r={5} fill={props.payload ? GROUP_COLOR[props.payload.group] : undefined} stroke="var(--card)" strokeWidth={2} />
            </g>
          )}
          onClick={(d: { payload?: Pt }) => d.payload && router.push(`/substitutes/${d.payload.id}`)}
          className="cursor-pointer"
        />
        {selected && (
          <Scatter
            name="selected"
            legendType="none"
            data={[toPt(selected)]}
            isAnimationActive={false}
            shape={(props: { cx?: number; cy?: number }) => (
              <g>
                <circle cx={props.cx} cy={props.cy} r={14} fill="var(--foreground)" fillOpacity={0.1} />
                <circle cx={props.cx} cy={props.cy} r={7} fill="var(--foreground)" stroke="var(--card)" strokeWidth={2} />
              </g>
            )}
          />
        )}
      </ScatterChart>
    </ChartContainer>
  )
}

function PointTooltip({ active, payload }: { active?: boolean; payload?: { payload: Pt }[] }) {
  const p = payload?.[0]?.payload
  if (!active || !p) return null
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <div className="flex items-center gap-1.5 font-medium">
        <span className="size-2 rounded-full" style={{ background: GROUP_COLOR[p.group] }} />
        {p.name}
      </div>
      <div className="mt-0.5 tabular-nums text-muted-foreground">
        PC1 {p.x.toFixed(2)} · PC2 {p.y.toFixed(2)}
      </div>
    </div>
  )
}
