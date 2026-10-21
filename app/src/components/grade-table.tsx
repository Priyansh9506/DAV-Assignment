"use client"

import { ArrowDownIcon, ArrowUpIcon, ChevronLeftIcon, ChevronRightIcon } from "lucide-react"
import Link from "next/link"
import * as React from "react"

import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { FORM_LABEL, GROUP_COLOR } from "@/lib/steel"
import type { GradeRow } from "@/lib/types"

type SortKey = "name" | "group" | "ts" | "ce" | "liquidus"
const PAGE = 12

/** Sortable, paginated grade table; every row links to the grade inspector. */
export function GradeTable({ rows, initialSort = "ts" }: { rows: GradeRow[]; initialSort?: SortKey }) {
  const [sort, setSort] = React.useState<{ key: SortKey; desc: boolean }>({ key: initialSort, desc: true })
  const [page, setPage] = React.useState(0)

  const sorted = React.useMemo(() => {
    const dir = sort.desc ? -1 : 1
    return [...rows].sort((a, b) => {
      const va = a[sort.key]
      const vb = b[sort.key]
      if (va == null) return 1
      if (vb == null) return -1
      return (typeof va === "string" ? va.localeCompare(vb as string) : (va as number) - (vb as number)) * dir
    })
  }, [rows, sort])

  const pages = Math.max(1, Math.ceil(sorted.length / PAGE))
  const current = Math.min(page, pages - 1)
  const slice = sorted.slice(current * PAGE, current * PAGE + PAGE)

  const header = (key: SortKey, label: string, numeric = false) => (
    <TableHead className={numeric ? "text-right" : undefined}>
      <button
        className="inline-flex items-center gap-1 hover:text-foreground"
        onClick={() => {
          setSort((s) => ({ key, desc: s.key === key ? !s.desc : numeric }))
          setPage(0)
        }}
      >
        {label}
        {sort.key === key && (sort.desc ? <ArrowDownIcon className="size-3" /> : <ArrowUpIcon className="size-3" />)}
      </button>
    </TableHead>
  )

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              {header("name", "Grade")}
              {header("group", "Group")}
              <TableHead>Form</TableHead>
              {header("ts", "Strength (MPa)", true)}
              {header("ce", "CE", true)}
              {header("liquidus", "Liquidus (°C)", true)}
            </TableRow>
          </TableHeader>
          <TableBody>
            {slice.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="max-w-[340px]">
                  <Link href={`/grades/${r.id}`} className="block truncate font-medium hover:text-primary hover:underline">
                    {r.name}
                  </Link>
                  <span className="text-xs text-muted-foreground">{r.familyLabel}</span>
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center gap-1.5 text-sm">
                    <span className="size-2 rounded-full" style={{ background: GROUP_COLOR[r.group] }} />
                    {r.group}
                  </span>
                </TableCell>
                <TableCell className="text-muted-foreground">{FORM_LABEL[r.form]}</TableCell>
                <TableCell className="text-right tabular-nums">{r.ts == null ? "n/a" : Math.round(r.ts)}</TableCell>
                <TableCell className="text-right tabular-nums">{r.ce.toFixed(2)}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {Math.round(r.liquidus)}
                  {r.liquidusDefault && <span className="ml-1 text-muted-foreground" title="Placeholder value, not measured">*</span>}
                </TableCell>
              </TableRow>
            ))}
            {slice.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                  No grades match the filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>* liquidus is the dataset&apos;s 1460 °C placeholder, not a grade-specific value</span>
        <div className="flex items-center gap-2">
          <span className="tabular-nums">
            Page {current + 1} of {pages}
          </span>
          <Button variant="outline" size="icon-sm" aria-label="Previous page" disabled={current === 0} onClick={() => setPage(current - 1)}>
            <ChevronLeftIcon />
          </Button>
          <Button variant="outline" size="icon-sm" aria-label="Next page" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}>
            <ChevronRightIcon />
          </Button>
        </div>
      </div>
    </div>
  )
}
