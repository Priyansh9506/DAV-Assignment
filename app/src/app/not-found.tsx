import Link from "next/link"

import { buttonVariants } from "@/components/ui/button"

export default function NotFound() {
  return (
    <div className="flex flex-col items-center gap-4 py-24 text-center">
      <h1 className="text-2xl font-semibold">That grade is not in the dataset</h1>
      <p className="text-muted-foreground">Try the search (Ctrl K) or start from the explorer.</p>
      <Link href="/" className={buttonVariants()}>
        Back to the explorer
      </Link>
    </div>
  )
}
