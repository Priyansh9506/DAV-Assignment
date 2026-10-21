import { ceTerms } from "@/lib/steel"

const W = 560
const H = 230
const LEFT = 40
const BOTTOM = 34
const TOP = 12

/**
 * Waterfall of the IIW carbon equivalent: each element's term stacks onto the running total, ending in the CE bar.
 * Dashed lines mark the 0.40 and 0.60 weldability thresholds. Server-rendered SVG; values are labelled directly.
 */
export function CeWaterfall({ comp, ce, color }: { comp: Record<string, number>; ce: number; color: string }) {
  const terms = ceTerms(comp).filter((t) => t.value > 0)
  const steps = [...terms, { label: "CE", value: ce }]
  const max = Math.max(ce, 0.7) * 1.12
  const plotW = W - LEFT - 8
  const slot = plotW / steps.length
  const bar = Math.min(slot * 0.62, 56)
  const y = (v: number) => TOP + (1 - v / max) * (H - TOP - BOTTOM)
  let run = 0

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={`Carbon equivalent build-up, total ${ce.toFixed(2)}`}>
      {[0.4, 0.6].map((t) =>
        t < max ? (
          <g key={t}>
            <line x1={LEFT} x2={W - 8} y1={y(t)} y2={y(t)} className="stroke-muted-foreground" strokeDasharray="4 4" strokeWidth={1} />
            <text x={W - 8} y={y(t) - 4} textAnchor="end" className="fill-muted-foreground text-[10px]">
              {t === 0.4 ? "0.40 preheat threshold" : "0.60 difficult"}
            </text>
          </g>
        ) : null,
      )}
      <line x1={LEFT} x2={W - 8} y1={y(0)} y2={y(0)} className="stroke-border" />
      {steps.map((s, i) => {
        const isTotal = i === steps.length - 1
        const from = isTotal ? 0 : run
        const to = isTotal ? s.value : run + s.value
        if (!isTotal) run = to
        const cx = LEFT + slot * i + slot / 2
        return (
          <g key={s.label}>
            <rect
              x={cx - bar / 2}
              y={y(to)}
              width={bar}
              height={Math.max(y(from) - y(to), 1.5)}
              rx={3}
              fill={isTotal ? color : "var(--muted-foreground)"}
              fillOpacity={isTotal ? 1 : 0.55}
            >
              <title>{`${s.label}: ${s.value.toFixed(3)}`}</title>
            </rect>
            <text x={cx} y={y(to) - 5} textAnchor="middle" className="fill-foreground text-[11px] tabular-nums">
              {isTotal ? s.value.toFixed(2) : `+${s.value.toFixed(2)}`}
            </text>
            <text x={cx} y={H - 12} textAnchor="middle" className="fill-muted-foreground text-[11px]">
              {s.label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
