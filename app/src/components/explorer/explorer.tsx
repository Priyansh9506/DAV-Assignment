"use client"

import { RotateCcwIcon, SearchIcon } from "lucide-react"
import * as React from "react"

import { StrengthBoxPlot } from "@/components/charts/box-plot"
import { GroupDonut } from "@/components/charts/group-donut"
import { StrengthHistogram } from "@/components/charts/strength-histogram"
import { GradeTable } from "@/components/grade-table"
import { StatTile } from "@/components/stat-tile"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { median, quantile } from "@/lib/stats"
import { FORM_LABEL, GROUP_COLOR, GROUP_ORDER } from "@/lib/steel"
import type { GradeRow, GroupName, ProductForm } from "@/lib/types"

const FORMS: Record<string, string> = { all: "All product forms", ...FORM_LABEL }

export function Explorer({ rows }: { rows: GradeRow[] }) {
  const bounds = React.useMemo<[number, number]>(() => {
    const tsValues = rows.flatMap((r) => (r.ts == null ? [] : [r.ts]))
    return [Math.min(...tsValues), Math.max(...tsValues)]
  }, [rows])

  const [groups, setGroups] = React.useState<GroupName[]>(GROUP_ORDER)
  const [form, setForm] = React.useState<string>("all")
  const [range, setRange] = React.useState<[number, number]>(bounds)
  const [query, setQuery] = React.useState("")

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase()
    const fullRange = range[0] === bounds[0] && range[1] === bounds[1]
    return rows.filter(
      (r) =>
        groups.includes(r.group) &&
        (form === "all" || r.form === (form as ProductForm)) &&
        (fullRange || (r.ts != null && r.ts >= range[0] && r.ts <= range[1])) &&
        (q === "" || r.name.toLowerCase().includes(q) || r.familyLabel.toLowerCase().includes(q)),
    )
  }, [rows, groups, form, range, query, bounds])

  const ts = filtered.flatMap((r) => (r.ts == null ? [] : [r.ts])).sort((a, b) => a - b)
  const reset = () => {
    setGroups(GROUP_ORDER)
    setForm("all")
    setRange(bounds)
    setQuery("")
  }

  return (
    <div className="space-y-6">
      <Card className="py-4">
        <CardContent className="flex flex-col gap-4 px-4">
          <div className="min-w-0 space-y-2">
            <span className="text-xs font-medium text-muted-foreground">Family groups</span>
            <ToggleGroup
              multiple
              value={groups}
              onValueChange={(v) => setGroups(v as GroupName[])}
              variant="outline"
              size="sm"
              className="flex-wrap"
            >
              {GROUP_ORDER.map((g) => (
                <ToggleGroupItem key={g} value={g} aria-label={g} className="gap-1.5">
                  <span className="size-2 rounded-full" style={{ background: GROUP_COLOR[g] }} />
                  {g}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </div>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
          <div className="w-full space-y-3 lg:w-72">
            <span className="text-xs font-medium text-muted-foreground">
              Tensile strength {range[0]}–{range[1]} MPa
            </span>
            <Slider
              min={bounds[0]}
              max={bounds[1]}
              step={10}
              value={range}
              onValueChange={(v) => setRange(v as [number, number])}
              aria-label="Tensile strength range"
            />
          </div>
          <div className="grid w-full grid-cols-2 gap-2 lg:flex lg:w-auto">
            <Select items={FORMS} value={form} onValueChange={(v) => setForm(v ?? "all")}>
              <SelectTrigger className="w-full lg:w-40" aria-label="Product form">
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
            <div className="relative">
              <SearchIcon className="absolute left-2.5 top-2 size-4 text-muted-foreground" />
              <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search name…" className="pl-8 lg:w-44" />
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={reset} className="self-start lg:self-end">
            <RotateCcwIcon /> Reset
          </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Grades in view" value={filtered.length.toLocaleString("en-US")} context={`of ${rows.length.toLocaleString("en-US")} canonical grades`} />
        <StatTile label="Median strength" value={ts.length ? Math.round(quantile(ts, 0.5)).toString() : "–"} unit="MPa" context={`${ts.length} grades with measured strength`} />
        <StatTile
          label="Middle 50 %"
          value={ts.length ? `${Math.round(quantile(ts, 0.25))}–${Math.round(quantile(ts, 0.75))}` : "–"}
          unit="MPa"
          context="interquartile range of strength"
        />
        <StatTile
          label="Median carbon equivalent"
          value={filtered.length ? median(filtered.map((r) => r.ce)).toFixed(2) : "–"}
          context="IIW CE; weldability gets harder above 0.40"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>How strong are they?</CardTitle>
            <CardDescription>Tensile strength of the grades in view, stacked by family group</CardDescription>
          </CardHeader>
          <CardContent>
            <StrengthHistogram rows={filtered} groups={groups} />
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Who is in the data?</CardTitle>
            <CardDescription>Grades per family group</CardDescription>
          </CardHeader>
          <CardContent>
            <GroupDonut rows={filtered} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Family decides the strength range</CardTitle>
          <CardDescription>Box = middle 50 %, line = median, whiskers = 1.5 × IQR, rings = outliers. Hover a row for its five numbers.</CardDescription>
        </CardHeader>
        <CardContent>
          <StrengthBoxPlot rows={filtered} groups={groups} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Grades</CardTitle>
          <CardDescription>Click a grade to inspect its chemistry and find substitutes</CardDescription>
        </CardHeader>
        <CardContent>
          <GradeTable rows={filtered} />
        </CardContent>
      </Card>
    </div>
  )
}
