export const THEME_STORAGE_KEY = "theme"

/**
 * Runs before first paint (inlined in <head> by the root layout): applies the saved theme, or the OS preference,
 * so the page never flashes the wrong colours.
 */
export const themeScript = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");var d=t?t==="dark":matchMedia("(prefers-color-scheme: dark)").matches;document.documentElement.classList.toggle("dark",d)}catch(e){}})()`
