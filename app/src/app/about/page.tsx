import type { Metadata } from "next"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { meta } from "@/lib/data"
import { GROUP_BLURB, GROUP_COLOR, GROUP_ORDER } from "@/lib/steel"

export const metadata: Metadata = { title: "About the data" }

const STEP_TITLE: Record<string, string> = {
  load_raw: "Load the raw file",
  validate_schema: "Validate the schema",
  drop_exact_duplicates: "Drop exact duplicates",
  flag_imputed_ts: "Flag the fake strength values",
  add_canonical_grade: "Match twin listings",
  collapse_to_grades: "Collapse to one row per grade",
  audit_processing_variants: "Audit processing variants",
  recompute_strength_class: "Rebuild the strength class",
}

export default function AboutPage() {
  const ex = meta.pca.explained
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">About the data</h1>
        <p className="text-muted-foreground">
          Where the numbers come from, how they were cleaned, and what the app can and cannot tell you. Every figure on
          this page is read from the files the data script writes, never typed in.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>From raw rows to canonical grades</CardTitle>
          <CardDescription>The cleaning log of notebook 01, step by step</CardDescription>
        </CardHeader>
        <CardContent>
          <ol className="space-y-3">
            {meta.cleaning.map((s, i) => (
              <li key={s.step} className="grid grid-cols-[1.5rem_1fr_auto] gap-3 text-sm">
                <span className="tabular-nums text-muted-foreground">{i + 1}</span>
                <div>
                  <div className="font-medium">{STEP_TITLE[s.step] ?? s.step.replaceAll("_", " ")}</div>
                  <div className="text-muted-foreground">{s.detail}</div>
                </div>
                <span className="tabular-nums">{s.rowsAfter.toLocaleString("en-US")} rows</span>
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Six family groups</CardTitle>
          <CardDescription>The same grouping as the notebooks, the Tableau workbook and the KNIME Rule Engine</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          {GROUP_ORDER.map((g) => (
            <div key={g} className="flex gap-3 rounded-lg border border-border p-3">
              <span className="mt-1 size-3 shrink-0 rounded-full" style={{ background: GROUP_COLOR[g] }} />
              <div>
                <div className="text-sm font-medium">{g}</div>
                <div className="text-xs text-muted-foreground">{GROUP_BLURB[g]}</div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Methods</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm leading-relaxed">
          <section>
            <h3 className="font-medium">Strength classes</h3>
            <p className="text-muted-foreground">
              Rebuilt from measured tensile strength:{" "}
              {meta.strengthClasses.map((c) => `${c.label} ${Math.round(c.min)}–${Math.round(c.max)} MPa`).join(" · ")}.
            </p>
          </section>
          <section>
            <h3 className="font-medium">Carbon equivalent</h3>
            <p className="text-muted-foreground">
              IIW formula CE = C + Mn/6 + (Cr + Mo + V)/5 + (Ni + Cu)/15. Weldability bands (≤ 0.40 readily weldable,
              ≤ 0.60 preheat advised, above that difficult) are shown only for carbon and low-alloy steels.
            </p>
          </section>
          <section>
            <h3 className="font-medium">Chemistry map and substitutes</h3>
            <p className="text-muted-foreground">
              The {meta.pcaFeatures.length} features are every element except iron and the {meta.rareElements.length}{" "}
              rare trace elements ({meta.rareElements.join(", ")}), plus their sum. Each is log-transformed (log 1 + x) and
              standardised. PCA keeps PC1 = {(ex[0] * 100).toFixed(1)} % and PC2 = {(ex[1] * 100).toFixed(1)} % of the
              variance; {meta.pca.componentsFor80} components are needed for 80 %, so the 2-D map is a summary, not the
              full picture. PC1 is driven by{" "}
              {meta.pca.topLoadings.PC1.map((l) => `${l.element} (${l.loading > 0 ? "+" : ""}${l.loading.toFixed(2)})`).join(", ")};
              PC2 by {meta.pca.topLoadings.PC2.map((l) => `${l.element} (${l.loading > 0 ? "+" : ""}${l.loading.toFixed(2)})`).join(", ")}.
              Substitutes are ranked by Euclidean distance in the full {meta.pcaFeatures.length}-feature space, not on the
              2-D map.
            </p>
          </section>
          <section>
            <h3 className="font-medium">Percentiles</h3>
            <p className="text-muted-foreground">
              Mid-rank percentiles: the share of grades with a lower value, counting ties as half.
            </p>
          </section>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Limits you should know</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
            <li>
              {meta.nGrades - meta.nMeasured} of {meta.nGrades.toLocaleString("en-US")} grades have no measured tensile
              strength; they appear in tables and on the chemistry map but in no strength statistic.
            </li>
            <li>
              {meta.nDefaultLiquidus} grades carry a {meta.defaultLiquidus} °C liquidus that is a placeholder, not a
              measurement. They are marked with * and left out of liquidus comparisons by default.
            </li>
            <li>
              The data records composition, not heat treatment, so grades with identical chemistry can differ in
              strength. The substitute finder is a shortlist, not an approval.
            </li>
            <li>
              The app does not predict properties. Machine learning for this project lives in the KNIME workflow, judged
              against simple baselines.
            </li>
          </ul>
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-2">
        {["Next.js 16", "React 19", "shadcn/ui", "Tailwind CSS 4", "Recharts", "Python data script"].map((t) => (
          <Badge key={t} variant="secondary">
            {t}
          </Badge>
        ))}
      </div>
    </div>
  )
}
