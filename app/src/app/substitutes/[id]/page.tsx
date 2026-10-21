import { InfoIcon } from "lucide-react"
import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"
import { Suspense } from "react"

import { PcaMap } from "@/components/charts/pca-map"
import { GradePicker } from "@/components/grade-picker"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { allGrades, getGrade, meta } from "@/lib/data"
import { GROUP_COLOR } from "@/lib/steel"

export function generateStaticParams() {
  return allGrades().map((g) => ({ id: g.id }))
}

export async function generateMetadata({ params }: PageProps<"/substitutes/[id]">): Promise<Metadata> {
  const { id } = await params
  const g = getGrade(id)
  return { title: g ? `Substitutes for ${g.name}` : "Grade not found" }
}

export default function SubstitutesPage({ params }: PageProps<"/substitutes/[id]">) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Substitute finder</h1>
        <p className="max-w-3xl text-muted-foreground">
          The ten grades whose chemistry is closest to the one you pick, measured in the same space as the PCA map:
          the {meta.pcaFeatures.length} non-rare alloying elements, log-transformed and standardised, compared by
          straight-line (Euclidean) distance.
        </p>
      </div>
      <Suspense fallback={<Skeleton className="h-[640px]" />}>
        <Substitutes params={params} />
      </Suspense>
    </div>
  )
}

async function Substitutes({ params }: { params: PageProps<"/substitutes/[id]">["params"] }) {
  const { id } = await params
  const grade = getGrade(id)
  if (!grade) notFound()
  const rows = grade.neighbours.map((n, i) => ({ ...n, rank: i + 1, g: getGrade(n.id)! }))
  const pct = (v: number) => `${(v * 100).toFixed(2)} %`
  const ex = meta.pca.explained

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <GradePicker name={grade.name} group={grade.group} hrefPrefix="/substitutes" />
        <div className="flex flex-wrap gap-4 text-sm">
          <span>
            <span className="text-muted-foreground">Strength </span>
            <b className="font-medium tabular-nums">{grade.ts == null ? "n/a" : `${Math.round(grade.ts)} MPa`}</b>
          </span>
          <span>
            <span className="text-muted-foreground">CE </span>
            <b className="font-medium tabular-nums">{grade.ce.toFixed(2)}</b>
          </span>
          <Link href={`/grades/${grade.id}`} className="underline-offset-4 hover:underline">
            Inspect this grade →
          </Link>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <CardHeader>
            <CardTitle>Ten closest grades</CardTitle>
            <CardDescription>Smaller distance = more similar chemistry. Strength difference is relative to the selected grade.</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8">#</TableHead>
                  <TableHead>Grade</TableHead>
                  <TableHead className="text-right">Distance</TableHead>
                  <TableHead className="text-right">Closer than</TableHead>
                  <TableHead className="text-right">Strength</TableHead>
                  <TableHead className="text-right">Δ strength</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => {
                  const delta = r.g.ts != null && grade.ts != null ? r.g.ts - grade.ts : null
                  return (
                    <TableRow key={r.id}>
                      <TableCell className="tabular-nums text-muted-foreground">{r.rank}</TableCell>
                      <TableCell className="max-w-[300px]">
                        <Link href={`/grades/${r.id}`} className="flex items-center gap-2 hover:text-primary hover:underline">
                          <span className="size-2 shrink-0 rounded-full" style={{ background: GROUP_COLOR[r.g.group] }} />
                          <span className="truncate">{r.g.name}</span>
                        </Link>
                        <div className="mt-1 flex gap-1.5">
                          {r.distance === 0 && <Badge variant="secondary">identical chemistry</Badge>}
                          {r.g.family !== grade.family && <Badge variant="outline">{r.g.familyLabel}</Badge>}
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{r.distance.toFixed(2)}</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">{pct(r.fartherShare)}</TableCell>
                      <TableCell className="text-right tabular-nums">{r.g.ts == null ? "n/a" : Math.round(r.g.ts)}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {delta == null ? "–" : (
                          <span className={Math.abs(delta) > 150 ? "text-destructive" : undefined}>
                            {delta > 0 ? "+" : ""}
                            {Math.round(delta)}
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
            <p className="mt-3 text-xs text-muted-foreground">
              &ldquo;Closer than&rdquo; = the share of all grade pairs in the dataset that are farther apart than this
              pair. Δ strength beyond ±150 MPa is shown in red.
            </p>
          </CardContent>
        </Card>
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>On the chemistry map</CardTitle>
            <CardDescription>Big dot = selected grade, rings = its ten substitutes. Click any point to search from it.</CardDescription>
          </CardHeader>
          <CardContent>
            <PcaMap
              selectedId={grade.id}
              highlightIds={grade.neighbours.map((n) => n.id)}
              axisLabels={[`PC1 (${(ex[0] * 100).toFixed(1)} % of variance)`, `PC2 (${(ex[1] * 100).toFixed(1)} %)`]}
            />
          </CardContent>
        </Card>
      </div>

      <Alert>
        <InfoIcon />
        <AlertTitle>Similar chemistry is a shortlist, not a guarantee</AlertTitle>
        <AlertDescription>
          Grades with identical composition can differ in strength because of heat treatment and product form, which the
          composition does not record. Check the strength column, and confirm with the standard before substituting.
        </AlertDescription>
      </Alert>
    </div>
  )
}
