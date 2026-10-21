"use client"

import { ChevronsUpDownIcon } from "lucide-react"
import * as React from "react"

import { GradeSearchDialog } from "@/components/grade-search"
import { Button } from "@/components/ui/button"
import { GROUP_COLOR } from "@/lib/steel"
import type { GroupName } from "@/lib/types"

/** A button showing the current grade that opens grade search; picking a grade navigates to `${hrefPrefix}/${id}`. */
export function GradePicker({ name, group, hrefPrefix }: { name: string; group: GroupName; hrefPrefix: string }) {
  const [open, setOpen] = React.useState(false)
  return (
    <>
      <Button variant="outline" size="lg" className="h-11 w-full justify-between gap-3 sm:w-[460px]" onClick={() => setOpen(true)}>
        <span className="flex min-w-0 items-center gap-2">
          <span className="size-2.5 shrink-0 rounded-full" style={{ background: GROUP_COLOR[group] }} />
          <span className="truncate">{name}</span>
        </span>
        <ChevronsUpDownIcon className="text-muted-foreground" />
      </Button>
      <GradeSearchDialog open={open} onOpenChange={setOpen} hrefPrefix={hrefPrefix} title="Pick a grade" />
    </>
  )
}
