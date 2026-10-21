import { Explorer } from "@/components/explorer/explorer"
import { gradeRows, meta } from "@/lib/data"

export default function ExplorerPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Explorer</h1>
        <p className="max-w-3xl text-muted-foreground">
          {meta.nGrades.toLocaleString("en-US")} steels and iron alloys. Filter by family, product form and strength;
          strength statistics use the {meta.nMeasured.toLocaleString("en-US")} grades with a measured value.
        </p>
      </div>
      <Explorer rows={gradeRows()} />
    </div>
  )
}
