"use client"

import * as React from "react"

import { THEME_STORAGE_KEY } from "@/lib/theme"

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange)
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] })
  return () => observer.disconnect()
}

/** Current theme, kept in sync with the `dark` class on <html>; null during server rendering. */
export function useTheme() {
  const dark = React.useSyncExternalStore(
    subscribe,
    () => document.documentElement.classList.contains("dark"),
    () => null,
  )
  const setDark = React.useCallback((next: boolean) => {
    document.documentElement.classList.toggle("dark", next)
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next ? "dark" : "light")
    } catch {}
  }, [])
  return { dark, setDark }
}
