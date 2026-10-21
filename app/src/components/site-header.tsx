"use client"

import { LayersIcon, MoonIcon, SearchIcon, SunIcon } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import * as React from "react"

import { Button } from "@/components/ui/button"
import { GradeSearchDialog } from "@/components/grade-search"
import { useTheme } from "@/hooks/use-theme"
import { FEATURED_GRADE_ID } from "@/lib/steel"
import { cn } from "@/lib/utils"

const NAV = [
  { href: "/", label: "Explorer" },
  { href: `/grades/${FEATURED_GRADE_ID}`, label: "Inspector", match: "/grades" },
  { href: `/substitutes/${FEATURED_GRADE_ID}`, label: "Substitutes", match: "/substitutes" },
  { href: "/designer", label: "Target designer" },
  { href: "/about", label: "About the data" },
]

export function SiteHeader() {
  const pathname = usePathname()
  const [open, setOpen] = React.useState(false)

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((o) => !o)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  return (
    <header className="sticky top-0 z-40 border-b bg-background">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span aria-hidden className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <LayersIcon className="size-4" />
          </span>
          SteelScope
        </Link>
        <nav className="hidden items-center gap-1 md:flex">
          {NAV.map((item) => {
            const active = item.match ? pathname.startsWith(item.match) : pathname === item.href
            return (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground",
                  active && "bg-muted text-foreground",
                )}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setOpen(true)} className="gap-2 text-muted-foreground">
            <SearchIcon />
            <span className="hidden sm:inline">Find a grade</span>
            <kbd className="hidden rounded border border-border px-1 font-mono text-[10px] sm:inline">Ctrl K</kbd>
          </Button>
          <ThemeToggle />
        </div>
      </div>
      <nav className="flex gap-1 overflow-x-auto px-4 pb-2 md:hidden">
        {NAV.map((item) => {
          const active = item.match ? pathname.startsWith(item.match) : pathname === item.href
          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "shrink-0 rounded-md px-2.5 py-1 text-xs text-muted-foreground",
                active && "bg-muted text-foreground",
              )}
            >
              {item.label}
            </Link>
          )
        })}
      </nav>
      <GradeSearchDialog open={open} onOpenChange={setOpen} />
    </header>
  )
}

function ThemeToggle() {
  const { dark, setDark } = useTheme()
  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      onClick={() => setDark(!dark)}
    >
      {dark ? <SunIcon /> : <MoonIcon />}
    </Button>
  )
}
