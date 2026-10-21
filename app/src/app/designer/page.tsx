import type { Metadata } from "next"

import { TargetDesigner } from "@/components/designer/target-designer"
import { gradeRows, meta } from "@/lib/data"

export const metadata: Metadata = { title: "Target designer" }

export default function DesignerPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Target designer</h1>
        <p className="max-w-3xl text-muted-foreground">
          Set the strength you need and the melting range your process can handle. The designer shows which families
          deliver it and lists every candidate grade, using only measured strengths ({meta.nMeasured.toLocaleString("en-US")}{" "}
          grades).
        </p>
      </div>
      <TargetDesigner rows={gradeRows()} defaultLiquidus={meta.defaultLiquidus} />
    </div>
  )
}
