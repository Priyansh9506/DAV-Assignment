"use client"

import * as React from "react"
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ReferenceArea, Scatter, ScatterChart, XAxis, YAxis, ZAxis } from "recharts"

import { GradeTable } from "@/components/grade-table"
import { StatTile } from "@/components/stat-tile"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { median } from "@/lib/stats"
import { FORM_LABEL, GROUP_CHART_CONFIG, GROUP_COLOR, GROUP_ORDER, GROUP_SHAPE } from "@/lib/steel"
import type { GradeRow, GroupName, ProductForm } from "@/lib/types"

const FORMS: Record<string, string> = { all: "Any product form", ...FORM_LABEL }

type Pt = { x: number; y: number; name: string; group: GroupName }

/** Requirement in, candidate families and grades out: strength window × liquidus window × product form. */
export function TargetDesigner({ rows, defaultLiquidus }: { rows: GradeRow[]; defaultLiquidus: number }) {
  const measured = rows.filter((r): r is GradeRow & { ts: number } => r.ts != null)
  const tsBounds: [number, number] = [Math.min(...measured.map((r) => r.ts)), Math.max(...measured.map((r) => r.ts))]
  const liqBounds: [number, number] = [Math.min(...rows.map((r) => r.liquidus)), Math.max(...rows.map((r) => r.liquidus))]

  const [ts, setTs] = React.useState<[number, number]>([800, 1200])
  const [liq, setLiq] = React.useState<[number, number]>([1400, 1500])
  const [form, setForm] = React.useState("all")
  const [skipPlaceholder, setSkipPlaceholder] = React.useState(true)

  const pool = measured.filter((r) => (form === "all" || r.form === (form as ProductForm)) && !(skipPlaceholder && r.liquidusDefault))
  const matches = pool.filter((r) => r.ts >= ts[0] && r.ts <= ts[1] && r.liquidus >= liq[0] && r.liquidus <= liq[1])
  const matchIds = new Set(matches.map((m) => m.id))
  const perGroup = GROUP_ORDER.map((g) => ({ group: g, count: matches.filter((m) => m.group === g).length })).filter((d) => d.count > 0)
  const toPt = (r: GradeRow & { ts: number }): Pt => ({ x: r.ts, y: r.liquidus, name: r.name, group: r.group })

  return (
    <div className="space-y-6">
      <Card className="py-4">
        <CardContent className="grid gap-6 px-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="space-y-3">
            <Label>
              Tensile strength: <span className="tabular-nums">{ts[0]}–{ts[1]} MPa</span>
            </Label>
            <Slider min={tsBounds[0]} max={tsBounds[1]} step={10} value={ts} onValueChange={(v) => setTs(v as [number, number])} aria-label="Tensile strength window" />
          </div>
          <div className="space-y-3">
            <Label>
              Liquidus: <span className="tabular-nums">{liq[0]}–{liq[1]} °C</span>
            </Label>
            <Slider min={liqBounds[0]} max={liqBounds[1]} step={5} value={liq} onValueChange={(v) => setLiq(v as [number, number])} aria-label="Liquidus window" />
          </div>
          <div className="space-y-2">
            <Label>Product form</Label>
            <Select items={FORMS} value={form} onValueChange={(v) => setForm(v ?? "all")}>
              <SelectTrigger className="w-full" aria-label="Product form">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(FORMS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-start gap-3">
            <Switch id="placeholder" checked={skipPlaceholder} onCheckedChange={setSkipPlaceholder} />
            <Label htmlFor="placeholder" className="block leading-snug font-normal">
              Ignore grades whose liquidus is the {defaultLiquidus} °C placeholder
              <span className="block text-xs text-muted-foreground">
                {measured.filter((r) => r.liquidusDefault).length} grades carry it instead of a real value
              </span>
            </Label>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Matching grades" value={matches.length.toString()} context={`out of ${pool.length} eligible grades`} />
        <StatTile label="Families that deliver" value={perGroup.length.toString()} context="family groups with at least one match" />
        <StatTile label="Median strength of matches" value={matches.length ? Math.round(median(matches.map((m) => m.ts))).toString() : "–"} unit="MPa" />
        <StatTile label="Median liquidus of matches" value={matches.length ? Math.round(median(matches.map((m) => m.liquidus))).toString() : "–"} unit="°C" />
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>The design space</CardTitle>
            <CardDescription>Every eligible grade by strength and liquidus; the box is your target, matches are drawn solid</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={GROUP_CHART_CONFIG} className="aspect-auto h-[380px] w-full">
              <ScatterChart margin={{ top: 8, right: 12, bottom: 24, left: 8 }}>
                <CartesianGrid strokeOpacity={0.4} />
                <XAxis type="number" dataKey="x" domain={[0, 2500]} tickLine={false} axisLine={false} label={{ value: "Tensile strength (MPa)", position: "insideBottom", offset: -14, className: "fill-muted-foreground text-[11px]" }} />
                <YAxis type="number" dataKey="y" domain={[1100, 1850]} tickLine={false} axisLine={false} width={44} label={{ value: "Liquidus (°C)", angle: -90, position: "insideLeft", className: "fill-muted-foreground text-[11px]" }} />
                <ZAxis range={[26, 26]} />
                <ReferenceArea x1={ts[0]} x2={ts[1]} y1={liq[0]} y2={liq[1]} fill="var(--foreground)" fillOpacity={0.05} stroke="var(--muted-foreground)" strokeDasharray="4 4" />
                <ChartTooltip cursor={false} content={<PointTooltip />} />
                {GROUP_ORDER.map((g) => (
                  <Scatter
                    key={g}
                    data={pool.filter((r) => r.group === g && !matchIds.has(r.id)).map(toPt)}
                    fill={GROUP_COLOR[g]}
                    fillOpacity={0.18}
                    shape={GROUP_SHAPE[g]}
                    isAnimationActive={false}
                  />
                ))}
                {GROUP_ORDER.map((g) => (
                  <Scatter
                    key={`m-${g}`}
                    data={matches.filter((r) => r.group === g).map(toPt)}
                    fill={GROUP_COLOR[g]}
                    stroke="var(--card)"
                    strokeWidth={1.5}
                    shape={GROUP_SHAPE[g]}
                    isAnimationActive={false}
                  />
                ))}
              </ScatterChart>
            </ChartContainer>
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Which families deliver it?</CardTitle>
            <CardDescription>Matching grades per family group</CardDescription>
          </CardHeader>
          <CardContent>
            {perGroup.length === 0 ? (
              <p className="py-16 text-center text-sm text-muted-foreground">No grade meets this target. Widen a window.</p>
            ) : (
              <ChartContainer config={GROUP_CHART_CONFIG} className="aspect-auto h-[300px] w-full">
                <BarChart data={perGroup} layout="vertical" margin={{ left: 8, right: 36 }}>
                  <XAxis type="number" hide allowDecimals={false} />
                  <YAxis type="category" dataKey="group" tickLine={false} axisLine={false} width={130} />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={22}>
                    {perGroup.map((d) => (
                      <Cell key={d.group} fill={GROUP_COLOR[d.group]} />
                    ))}
                    <LabelList dataKey="count" position="right" className="fill-foreground text-xs tabular-nums" />
                  </Bar>
                </BarChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Candidate grades</CardTitle>
          <CardDescription>Every grade inside the target box; click one to inspect it</CardDescription>
        </CardHeader>
        <CardContent>
          <GradeTable rows={matches} />
        </CardContent>
      </Card>
    </div>
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
        {Math.round(p.x)} MPa · {Math.round(p.y)} °C
      </div>
    </div>
  )
}
