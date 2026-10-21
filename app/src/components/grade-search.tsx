"use client"

import { useRouter } from "next/navigation"

import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { loadSearchIndex, useLoaded } from "@/lib/client-data"
import { GROUP_COLOR } from "@/lib/steel"

/** Command-palette grade search; selecting a grade navigates to `${hrefPrefix}/${id}`. */
export function GradeSearchDialog({
  open,
  onOpenChange,
  hrefPrefix = "/grades",
  title = "Find a grade",
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  hrefPrefix?: string
  title?: string
}) {
  const items = useLoaded(loadSearchIndex, open)
  const router = useRouter()
  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} title={title} description="Search every grade by name">
      <Command>
        <CommandInput placeholder="Type a grade, e.g. 4140, 316L, S355…" />
        <CommandList>
          <CommandEmpty>{items ? "No grade matches." : "Loading grades…"}</CommandEmpty>
          {items && (
            <CommandGroup heading={`${items.length.toLocaleString("en-US")} grades`}>
              {items.map((g) => (
                <CommandItem
                  key={g.id}
                  value={`${g.name} ${g.id}`}
                  onSelect={() => {
                    onOpenChange(false)
                    router.push(`${hrefPrefix}/${g.id}`)
                  }}
                >
                  <span className="size-2 shrink-0 rounded-full" style={{ background: GROUP_COLOR[g.group] }} />
                  <span className="truncate">{g.name}</span>
                  <span className="ml-auto text-xs text-muted-foreground">{g.group}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
        </CommandList>
      </Command>
    </CommandDialog>
  )
}
