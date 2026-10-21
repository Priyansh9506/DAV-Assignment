"use client"

import * as React from "react"

export type HoverInfo = { x: number; y: number; title: string; color?: string; lines: string[] }

/** Positions a small tooltip card at the pointer, relative to a `relative` wrapper. Used by the custom SVG charts. */
export function useHover() {
  const ref = React.useRef<HTMLDivElement>(null)
  const [hover, setHover] = React.useState<HoverInfo | null>(null)
  const show = (e: React.MouseEvent, info: Omit<HoverInfo, "x" | "y">) => {
    const box = ref.current?.getBoundingClientRect()
    if (!box) return
    setHover({ ...info, x: e.clientX - box.left, y: e.clientY - box.top })
  }
  return { ref, hover, show, hide: () => setHover(null) }
}

export function HoverCard({ hover }: { hover: HoverInfo | null }) {
  if (!hover) return null
  return (
    <div
      className="pointer-events-none absolute z-10 min-w-36 -translate-x-1/2 -translate-y-[calc(100%+12px)] rounded-lg border bg-popover px-3 py-2 text-xs shadow-lg"
      style={{ left: hover.x, top: hover.y }}
    >
      <div className="flex items-center gap-1.5 font-medium">
        {hover.color && <span className="size-2.5 shrink-0 rounded-full" style={{ background: hover.color }} />}
        {hover.title}
      </div>
      {hover.lines.map((l) => (
        <div key={l} className="mt-0.5 tabular-nums text-muted-foreground">
          {l}
        </div>
      ))}
    </div>
  )
}
