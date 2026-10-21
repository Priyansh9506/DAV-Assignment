import { ArrowRightIcon, InfoIcon } from "lucide-react"
import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"
import { Suspense } from "react"

import { CeWaterfall } from "@/components/charts/ce-waterfall"
import { CompositionRadar } from "@/components/charts/composition-radar"
import { CompositionBars } from "@/components/composition-bars"
import { PercentileBars } from "@/components/percentile-bars"
import { StatTile } from "@/components/stat-tile"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { allGrades, compositionRadar, getGrade, meta, standings } from "@/lib/data"
import { ceBand, FORM_LABEL, GROUP_BLURB, GROUP_COLOR, STRENGTH_CLASS_LABEL } from "@/lib/steel"

export function generateStaticParams() {
  return allGrades().map((g) => ({ id: g.id }))
}

export async function generateMetadata({ params }: PageProps<"/grades/[id]">): Promise<Metadata> {
  const { id } = await params
  return { title: getGrade(id)?.name ?? "Grade not found" }
}

// Fixed status hues (good / warning / critical), used only as a dot beside the text label.
const TONE: Record<string, string> = { good: "#0ca30c", warning: "#fab219", critical: "#d03b3b" }

export default function GradePage({ params }: PageProps<"/grades/[id]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <GradeView params={params} />
    </Suspense>
  )
}

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-9 w-2/3" />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-80" />
        <Skeleton className="h-80" />
      </div>
    </div>
  )
}

async function GradeView({ params }: { params: PageProps<"/grades/[id]">["params"] }) {
  const { id } = await params
  const grade = getGrade(id)
  if (!grade) notFound()

  const color = GROUP_COLOR[grade.group]
  const band = ceBand(grade.ce)
  const plainSteel = grade.group === "Carbon & low-alloy"
  const neighbours = grade.neighbours.slice(0, 5).map((n) => ({ ...n, grade: getGrade(n.id)! }))

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
          ← Explorer
        </Link>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight">{grade.name}</h1>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="gap-1.5">
                <span className="size-2 rounded-full" style={{ background: color }} />
                {grade.group}
              </Badge>
              <Badge variant="secondary">{grade.familyLabel}</Badge>
              <Badge variant="secondary">{FORM_LABEL[grade.form]}</Badge>
              <Badge variant="secondary">{grade.standard} designation</Badge>
            </div>
            <p className="text-sm text-muted-foreground">{GROUP_BLURB[grade.group]}</p>
          </div>
          <Link href={`/substitutes/${grade.id}`} className={buttonVariants({ size: "lg" })}>
            Find substitutes <ArrowRightIcon />
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile
          label="Tensile strength"
          value={grade.ts == null ? "n/a" : Math.round(grade.ts).toString()}
          unit={grade.ts == null ? undefined : "MPa"}
          context={grade.strengthClass == null ? "no measured value in the source data" : `class ${STRENGTH_CLASS_LABEL[grade.strengthClass]}`}
        />
        <StatTile
          label="Carbon equivalent"
          value={grade.ce.toFixed(2)}
          context={
            plainSteel ? (
              <Badge variant="outline" className="gap-1.5">
                <span className="size-2 rounded-full" style={{ background: TONE[band.tone] }} />
                {band.label}
              </Badge>
            ) : (
              "weldability bands apply to plain steels only"
            )
          }
        />
        <StatTile
          label="Liquidus"
          value={Math.round(grade.liquidus).toString()}
          unit="°C"
          context={grade.liquidusDefault ? `${meta.defaultLiquidus} °C placeholder, not grade-specific` : "temperature at which it is fully molten"}
        />
        <StatTile
          label="Alloying total"
          value={grade.alloyTotal.toFixed(2)}
          unit="wt%"
          context={grade.chemTwins > 0 ? `${grade.chemTwins} other grade(s) share this exact chemistry` : "everything that is not iron"}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Where it stands</CardTitle>
            <CardDescription>Percentile within the {grade.familyLabel.toLowerCase()} family and among all grades</CardDescription>
          </CardHeader>
          <CardContent>
            <PercentileBars standings={standings(grade)} familyLabel={grade.familyLabel} color={color} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Chemical fingerprint</CardTitle>
            <CardDescription>Each axis: the element&apos;s percentile among all {meta.nGrades.toLocaleString("en-US")} grades</CardDescription>
          </CardHeader>
          <CardContent>
            <CompositionRadar data={compositionRadar(grade)} gradeName={grade.name} group={grade.group} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Composition</CardTitle>
            <CardDescription>Every element present, in weight percent</CardDescription>
          </CardHeader>
          <CardContent>
            <CompositionBars comp={grade.comp} alloyTotal={grade.alloyTotal} color={color} />
          </CardContent>
        </Card>
        <div className="space-y-6 lg:col-span-3">
          <Card>
            <CardHeader>
              <CardTitle>How the carbon equivalent adds up</CardTitle>
              <CardDescription>CE = C + Mn/6 + (Cr + Mo + V)/5 + (Ni + Cu)/15 (IIW). Dashed lines: 0.40 preheat threshold, 0.60 difficult.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <CeWaterfall comp={grade.comp} ce={grade.ce} color={color} />
              {plainSteel ? (
                <p className="text-sm text-muted-foreground">{band.advice}</p>
              ) : (
                <Alert>
                  <InfoIcon />
                  <AlertDescription>
                    The IIW weldability bands are calibrated for carbon and low-alloy steels; for {grade.group.toLowerCase()} the
                    CE is shown for comparison only.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Closest chemistry</CardTitle>
              <CardDescription>The five nearest grades in composition space</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="divide-y divide-border">
                {neighbours.map((n) => (
                  <li key={n.id} className="flex items-center gap-3 py-2 text-sm">
                    <span className="size-2 shrink-0 rounded-full" style={{ background: GROUP_COLOR[n.grade.group] }} />
                    <Link href={`/grades/${n.id}`} className="min-w-0 flex-1 truncate hover:text-primary hover:underline">
                      {n.grade.name}
                    </Link>
                    <span className="font-mono text-xs tabular-nums text-muted-foreground">
                      {n.distance === 0 ? "identical" : `d = ${n.distance.toFixed(2)}`}
                    </span>
                    <span className="w-20 text-right tabular-nums">{n.grade.ts == null ? "n/a" : `${Math.round(n.grade.ts)} MPa`}</span>
                  </li>
                ))}
              </ul>
              <Link href={`/substitutes/${grade.id}`} className={`${buttonVariants({ variant: "link" })} mt-2 px-0`}>
                All ten, on the chemistry map <ArrowRightIcon />
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
