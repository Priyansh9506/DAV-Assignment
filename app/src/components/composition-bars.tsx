import { ELEMENT_NAME, fmt } from "@/lib/steel"

/** Alloying elements as a share of everything that is not iron, largest first. */
export function CompositionBars({ comp, alloyTotal, color }: { comp: Record<string, number>; alloyTotal: number; color: string }) {
  const items = Object.entries(comp)
    .filter(([el]) => el !== "Fe")
    .sort((a, b) => b[1] - a[1])
  const top = items[0]?.[1] ?? 1
  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-muted-foreground">Iron (balance)</span>
        <span className="tabular-nums">{fmt.wt(comp.Fe ?? 0)} wt%</span>
      </div>
      <ul className="space-y-1.5">
        {items.map(([el, v]) => (
          <li key={el} className="grid grid-cols-[2.5rem_1fr_4.5rem] items-center gap-2 text-sm" title={ELEMENT_NAME[el] ?? el}>
            <span className="font-medium">{el}</span>
            <span className="h-2 rounded-full bg-muted">
              <span className="block h-full rounded-full" style={{ width: `${Math.max((v / top) * 100, 1.5)}%`, background: color }} />
            </span>
            <span className="text-right tabular-nums">{fmt.wt(v)}</span>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">
        wt%. Bars are scaled to the largest alloying element; together they make up {fmt.wt(alloyTotal)} wt% of the steel.
      </p>
    </div>
  )
}
