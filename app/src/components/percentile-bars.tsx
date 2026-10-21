import type { Standing } from "@/lib/data"

/** Where a grade sits within its family (filled bar) and within all grades (tick), on a 0-100 percentile scale. */
export function PercentileBars({ standings, familyLabel, color }: { standings: Standing[]; familyLabel: string; color: string }) {
  return (
    <div className="space-y-5">
      {standings.map((s) => (
        <div key={s.metric} className="space-y-1.5">
          <div className="flex items-baseline justify-between gap-2 text-sm">
            <span className="font-medium">{s.metric}</span>
            <span className="tabular-nums">
              {s.unit === "MPa" || s.unit === "°C" ? Math.round(s.value) : s.value.toFixed(2)}
              {s.unit && <span className="ml-1 text-muted-foreground">{s.unit}</span>}
            </span>
          </div>
          <div className="relative h-2.5 rounded-full bg-muted">
            <div className="h-full rounded-full" style={{ width: `${s.inFamily}%`, background: color }} />
            <div
              className="absolute -top-1 h-4.5 w-0.5 rounded-full bg-foreground"
              style={{ left: `calc(${s.inAll}% - 1px)` }}
              title={`Percentile among all grades: ${Math.round(s.inAll)}`}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>
              Higher than <b className="text-foreground">{Math.round(s.inFamily)} %</b> of {familyLabel.toLowerCase()} grades
            </span>
            <span>
              {Math.round(s.inAll)} % of all · family median {s.unit === "MPa" || s.unit === "°C" ? Math.round(s.familyMedian) : s.familyMedian.toFixed(2)}
            </span>
          </div>
        </div>
      ))}
      <p className="text-xs text-muted-foreground">Bar = percentile within the family · white tick = percentile among all grades.</p>
    </div>
  )
}
