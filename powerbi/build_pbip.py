"""Build the SteelScope Power BI report as a Power BI Project (PBIP) that Power BI Desktop opens directly.

Reads  powerbi/measures.dax, powerbi/queries.pq, powerbi/SteelScope.theme.json, powerbi/data/families.csv
Writes powerbi/SteelScope.pbip                  open this in Power BI Desktop
       powerbi/SteelScope.SemanticModel/        TMDL model: 4 tables, 3 relationships, measures, DataFolder parameter
       powerbi/SteelScope.Report/               PBIR report: the six pages of POWERBI_GUIDE.md, every visual placed

The DataFolder parameter is set to this machine's absolute powerbi/data/ path, so re-run the script after moving or
cloning the project. Then open SteelScope.pbip and press Home -> Refresh once to load the data.

Run from the project root:  python powerbi/build_pbip.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "powerbi"
DATA = PBI / "data"
NAME = "SteelScope"
MODEL = PBI / f"{NAME}.SemanticModel"
REPORT = PBI / f"{NAME}.Report"
# Base theme shipped with Power BI Desktop; the report references it the same way Desktop does.
BASE_THEME = "CY26SU10"
THEMES_IN_BIN = Path("bin/WebView2Resources/minerva/sharedresources/BaseThemes")

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/"
V_VISUAL, V_PAGE, V_REPORT = "2.7.0", "2.1.0", "3.2.0"

# ---------------------------------------------------------------- semantic model

MEASURE_FORMAT = {
    "Grades": "#,0", "Measured grades": "#,0", "Median strength (MPa)": "#,0", "Mean strength (MPa)": "#,0.0",
    "Q1 strength (MPa)": "#,0", "Q3 strength (MPa)": "#,0", "Median carbon equivalent": "0.00",
    "Share of grades": "0.0%", "High-strength share": "0.0%", "Readily weldable share (plain steels)": "0.0%",
    "Average wt %": "0.000", "Element intensity": "0%", "Placeholder liquidus grades": "#,0",
}
M_TYPE = {"type text": "string", "type number": "double", "type logical": "boolean", "Int64.Type": "int64"}
HIDDEN = {("grades", "strength_class_order"), ("families", "group_order"), ("families", "group_color"),
          ("composition", "grade_id")}
SORT_BY = {("families", "family_group"): "group_order", ("grades", "strength_class"): "strength_class_order"}
# Bin column with the name Power BI's "New group -> Bin, size 100" would give it (POWERBI_GUIDE.md step 2).
BIN = "tensile_strength_mpa (bins)"
BIN_DAX = "IF ( NOT ISBLANK ( grades[tensile_strength_mpa] ), FLOOR ( grades[tensile_strength_mpa], 100 ) )"
RELATIONSHIPS = [("grades", "family", "families", "family"), ("composition", "grade_id", "grades", "grade_id"),
                 ("composition", "element", "elements", "element")]


def tag(*parts: str) -> str:
    """Stable lineage tag, so re-running the script produces no diff."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "steelscope/" + "/".join(parts)))


def q(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"


def parse_measures() -> dict[str, str]:
    """measures.dax: blocks separated by blank lines, `Name = expression`, `//` lines are comments."""
    text = (PBI / "measures.dax").read_text(encoding="utf-8")
    measures = {}
    for block in re.split(r"\n\s*\n", text):
        lines = [ln for ln in block.splitlines() if not ln.lstrip().startswith("//")]
        if not lines:
            continue
        name, first = re.match(r"(.+?) =(.*)", lines[0]).groups()
        measures[name.strip()] = "\n".join([first.strip(), *lines[1:]]).strip()
    return measures


def parse_queries() -> dict[str, str]:
    text = (PBI / "queries.pq").read_text(encoding="utf-8")
    parts = re.split(r"^// ===== Query: (\w+) =====\s*$", text, flags=re.M)
    return {parts[i]: "\n".join(ln for ln in parts[i + 1].strip().splitlines() if not ln.startswith("//")).strip()
            for i in range(1, len(parts), 2)}


def columns_of(m_query: str) -> list[tuple[str, str]]:
    return [(c, M_TYPE[t]) for c, t in re.findall(r'\{"(\w+)",\s*(type \w+|Int64\.Type)\}', m_query)]


def indent(text: str, tabs: int) -> str:
    return "\n".join("\t" * tabs + ln if ln.strip() else "" for ln in text.splitlines())


def table_tmdl(table: str, m_query: str, measures: dict[str, str]) -> str:
    out = [f"table {table}", f"\tlineageTag: {tag(table)}", ""]
    for name, expr in measures.items():
        head = f"\tmeasure {q(name)} ="
        out.append(f"{head} {expr}" if "\n" not in expr else f"{head}\n{indent(expr, 3)}")
        if name in MEASURE_FORMAT:  # text measures such as "Middle 50 % (MPa)" carry no format string
            out.append(f"\t\tformatString: {MEASURE_FORMAT[name]}")
        out += [f"\t\tlineageTag: {tag(table, 'm', name)}", ""]
    for col, dtype in columns_of(m_query):
        out += [f"\tcolumn {q(col)}", f"\t\tdataType: {dtype}"]
        if dtype == "double":
            out.append("\t\tformatString: 0.####")
        if (table, col) in HIDDEN:
            out.append("\t\tisHidden")
        out += [f"\t\tlineageTag: {tag(table, col)}", "\t\tsummarizeBy: none", f"\t\tsourceColumn: {col}"]
        if (table, col) in SORT_BY:
            out.append(f"\t\tsortByColumn: {SORT_BY[(table, col)]}")
        out += ["", "\t\tannotation SummarizationSetBy = User", ""]
    if table == "grades":
        out += [f"\tcolumn {q(BIN)} = {BIN_DAX}", "\t\tdataType: double", "\t\tformatString: 0",
                f"\t\tlineageTag: {tag(table, BIN)}", "\t\tsummarizeBy: none", "",
                "\t\tannotation SummarizationSetBy = User", ""]
    out += [f"\tpartition {table} = m", "\t\tmode: import", "\t\tsource =", indent(m_query, 4), "",
            "\tannotation PBI_ResultType = Table", ""]
    return "\n".join(out)


def write_model() -> None:
    measures, queries = parse_measures(), parse_queries()
    folder = str(DATA) + "\\"
    defn = MODEL / "definition"
    (defn / "tables").mkdir(parents=True)
    write_json(MODEL / "definition.pbism", {
        "$schema": SCHEMA + "item/semanticModel/definitionProperties/1.0.0/schema.json", "version": "4.2",
        "settings": {}})
    (defn / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1567\n\n", encoding="utf-8")
    order = ["DataFolder", *queries]
    (defn / "model.tmdl").write_text("\n".join([
        "model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tsourceQueryCulture: en-US", "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
        f"annotation PBI_QueryOrder = {json.dumps(order, separators=(',', ':'))}", "",
        "annotation __PBI_TimeIntelligenceEnabled = 0", "",
        "annotation PBI_ProTooling = [\"DevMode\"]", "",
        *[f"ref table {t}" for t in queries], ""]), encoding="utf-8")
    (defn / "expressions.tmdl").write_text("\n".join([
        f'expression DataFolder = "{folder}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
        f"\tlineageTag: {tag('DataFolder')}", "", "\tannotation PBI_ResultType = Text", ""]), encoding="utf-8")
    (defn / "relationships.tmdl").write_text("\n".join(
        line for f, fc, t, tc in RELATIONSHIPS
        for line in (f"relationship {tag('rel', f, fc)}", f"\tfromColumn: {f}.{fc}", f"\ttoColumn: {t}.{tc}", "")),
        encoding="utf-8")
    for table, m_query in queries.items():
        (defn / "tables" / f"{table}.tmdl").write_text(
            table_tmdl(table, m_query, measures if table == "grades" else {}), encoding="utf-8")


# ---------------------------------------------------------------- report: query and formatting helpers

def col(table, column):
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": column}}


def meas(name, table="grades"):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


AGG = {"Sum": 0, "Avg": 1, "Min": 3, "Max": 4}


def agg(table, column, fn):
    return {"Aggregation": {"Expression": col(table, column), "Function": AGG[fn]}}


def ref(field) -> str:
    """queryRef in the form Desktop writes it: Table.Field, or Fn(Table.Field) for an aggregation."""
    if "Aggregation" in field:
        a = field["Aggregation"]
        fn = next(k for k, v in AGG.items() if v == a["Function"])
        return f"{fn}({ref(a['Expression'])})"
    kind = "Column" if "Column" in field else "Measure"
    return f"{field[kind]['Expression']['SourceRef']['Entity']}.{field[kind]['Property']}"


def proj(field, name=None):
    p = {"field": field, "queryRef": ref(field), "nativeQueryRef": ref(field).split(".")[-1].rstrip(")")}
    if name:
        p["displayName"] = name
    return p


def lit(value):
    if value is None:
        return {"Literal": {"Value": "null"}}
    if isinstance(value, bool):
        return {"Literal": {"Value": "true" if value else "false"}}
    if isinstance(value, int):
        return {"Literal": {"Value": f"{value}L"}}
    if isinstance(value, float):
        return {"Literal": {"Value": f"{value:g}D"}}  # 800D, as Desktop writes it (800.0D is not read back)
    return {"Literal": {"Value": "'" + str(value).replace("'", "''") + "'"}}


def L(value):
    return {"expr": lit(value)}


def solid(hex_color):
    return {"solid": {"color": L(hex_color)}}


def props(**kw):
    return [{"properties": {k: (v if isinstance(v, dict) and ("expr" in v or "solid" in v) else L(v))
                            for k, v in kw.items()}}]


def scoped_colors(table, column, colors: dict[str, str]):
    """dataPoint fills keyed on a category or legend value (Format -> Colors in Desktop)."""
    return [{"properties": {"fill": solid(c)},
             "selector": {"data": [{"scopeId": {"Comparison": {
                 "ComparisonKind": 0, "Left": col(table, column), "Right": lit(v)}}}]}} for v, c in colors.items()]


def column_widths(widths: dict[str, float]):
    return [{"properties": {"value": L(float(w))}, "selector": {"metadata": q}} for q, w in widths.items()]


def measure_colors(colors: dict[str, str]):
    return [{"properties": {"fill": solid(c)}, "selector": {"metadata": f"grades.{m}"}} for m, c in colors.items()]


def condition(table, column, values, negate=False):
    cond = {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": column}}],
                   "Values": [[lit(v)] for v in values]}}
    return {"Not": {"Expression": cond}} if negate else cond


def where(table, cond):
    return {"Version": 2, "From": [{"Name": "t", "Entity": table, "Type": 0}], "Where": [{"Condition": cond}]}


def visual_filter(key, table, column, values, negate=False):
    return {"name": uid("filter", key), "field": col(table, column), "type": "Categorical",
            "filter": where(table, condition(table, column, values, negate)), "howCreated": "User"}


def uid(*parts) -> str:
    return hashlib.md5("/".join(parts).encode()).hexdigest()[:20]


# ---------------------------------------------------------------- report: visuals

class Page:
    def __init__(self, name, display, title, question):
        self.name, self.display, self.visuals = name, display, []
        self.page_extra = {}
        self.text("header", 16, 8, 640, 54, [(title, "16pt", "#1F1F1F", True), (question, "10pt", "#6B6B6B", False)])

    def add(self, key, vtype, x, y, w, h, query=None, objects=None, title=None, subtitle=None, filters=None,
            container=None, sort=None):
        visual = {"visualType": vtype}
        if query:
            visual["query"] = {"queryState": {role: {"projections": ps} for role, ps in query.items()}}
            if sort:
                visual["query"]["sortDefinition"] = {
                    "sort": [{"field": f, "direction": d} for f, d in sort], "isDefaultSort": False}
        if objects:
            visual["objects"] = objects
        vco = dict(container or {})
        if title is not None:
            vco["title"] = props(show=True, text=title)
        if subtitle:
            vco["subTitle"] = props(show=True, text=subtitle)
        if vco:
            visual["visualContainerObjects"] = vco
        visual["drillFilterOtherVisuals"] = True
        name = uid(self.name, key)
        body = {"$schema": f"{SCHEMA}item/report/definition/visualContainer/{V_VISUAL}/schema.json", "name": name,
                "position": {"x": x, "y": y, "z": len(self.visuals) * 1000, "height": h, "width": w,
                             "tabOrder": len(self.visuals) * 1000},
                "visual": visual}
        if filters:
            body["filterConfig"] = {"filters": filters}
        self.visuals.append(body)

    def text(self, key, x, y, w, h, runs, panel=False):
        paragraphs = [{"textRuns": [{"value": t, "textStyle": {
            "fontSize": size, "color": color, "fontFamily": "Segoe UI Semibold" if bold else "Segoe UI"}}]}
            for t, size, color, bold in runs]
        container = {"background": props(show=True, color=solid("#FFFFFF")),
                     "border": props(show=True, color=solid("#E3E1DC"), radius=8.0),
                     "padding": props(top=12.0, bottom=12.0, left=14.0, right=14.0)} if panel else None
        self.add(key, "textbox", x, y, w, h, objects={"general": [{"properties": {"paragraphs": paragraphs}}]},
                 container=container)

    def nav(self):
        self.add("nav", "pageNavigator", 664, 12, 600, 44,
                 container={"background": props(show=False), "border": props(show=False)})

    def card(self, key, x, y, w, h, field, label, font=None):
        labels = {"labelDisplayUnits": 1.0}  # 1,160 rather than 1.16K
        if font:
            labels["fontSize"] = float(font)
        self.add(key, "card", x, y, w, h, query={"Values": [proj(field, label)]},
                 objects={"labels": props(**labels)}, container={"title": props(show=False)})

    def slicer(self, key, x, y, w, h, field, label, mode, selected=None):
        objects = {"data": props(mode=mode)}
        if selected:
            objects["general"] = [{"properties": {"filter": {"filter": selected}}}]
        self.add(key, "slicer", x, y, w, h, query={"Values": [proj(field, label)]}, objects=objects,
                 container={"title": props(show=False)})


def build_pages(group_colors: dict[str, str]) -> list[Page]:
    fg = col("families", "family_group")
    group = proj(fg, "Family group")
    legend = props(show=True, position="Top", showTitle=False)
    no_axis_title = props(showAxisTitle=False)
    group_dp = scoped_colors("families", "family_group", group_colors)
    class_dp = scoped_colors("grades", "strength_class", {
        "Low (< 300 MPa)": "#a6c8ef", "Medium (300-600 MPa)": "#4a8fdc", "High (> 600 MPa)": "#104281"})
    weld_dp = scoped_colors("grades", "weldability_band", {
        "Readily weldable (CE <= 0.40)": "#1baf7a", "Preheat advised (0.40-0.60)": "#eda100",
        "Difficult (CE > 0.60)": "#e34948"})
    pages = []

    # 1 · Overview
    p = Page("overview", "Overview", "SteelScope · 1,389 steel grades",
             "What is in the data and how strong is it?")
    p.nav()
    p.slicer("s_group", 16, 68, 184, 76, fg, "Family group", "Dropdown")
    p.slicer("s_form", 208, 68, 144, 76, col("grades", "product_form"), "Product form", "Dropdown")
    p.slicer("s_strength", 360, 68, 252, 76, col("grades", "tensile_strength_mpa"), "Tensile strength (MPa)",
             "Between")
    for i, (key, m, label) in enumerate([("c_grades", "Grades", "Grades in view"),
                                         ("c_median", "Median strength (MPa)", "Median strength, MPa"),
                                         ("c_iqr", "Middle 50 % (MPa)", "Middle 50 %, MPa"),
                                         ("c_ce", "Median carbon equivalent", "Median carbon equiv.")]):
        p.card(key, 620 + i * 163, 68, 155, 76, meas(m), label)
    p.add("histogram", "columnChart", 16, 152, 676, 560,
          query={"Category": [proj(col("grades", BIN), "Tensile strength (MPa, 100-wide bins)")],
                 "Y": [proj(meas("Grades"))], "Series": [group]},
          sort=[(col("grades", BIN), "Ascending")],
          objects={"dataPoint": group_dp, "categoryAxis": props(axisType="Categorical"), "legend": legend},
          title="How strong are they?", subtitle="Most grades sit between 400 and 800 MPa, with a long tail to 2,450",
          filters=[visual_filter("ov_bins", "grades", BIN, [None], negate=True)])
    p.add("treemap", "treemap", 700, 152, 564, 276,
          query={"Group": [group], "Details": [proj(col("families", "family_label"), "Family")],
                 "Values": [proj(meas("Grades"))]},
          objects={"dataPoint": group_dp, "legend": props(show=False), "labels": props(show=True)},
          title="Who is in the data?", subtitle="Stainless (546) and alloy steel (293) are the biggest families")
    p.add("quartiles", "clusteredColumnChart", 700, 436, 564, 276,
          query={"Category": [group], "Y": [proj(meas("Q1 strength (MPa)"), "Q1"),
                                            proj(meas("Median strength (MPa)"), "Median"),
                                            proj(meas("Q3 strength (MPa)"), "Q3")]},
          sort=[(fg, "Ascending")],
          objects={"dataPoint": measure_colors({"Q1 strength (MPa)": "#a6c8ef", "Median strength (MPa)": "#104281",
                                                "Q3 strength (MPa)": "#4a8fdc"}),
                   "legend": legend, "categoryAxis": no_axis_title, "valueAxis": no_axis_title},
          title="Strength quartiles by family group (MPa)",
          subtitle="Cast iron is the weakest group, maraging / Fe-Ni (Other) the strongest")
    pages.append(p)

    # 2 · Families and strength classes
    p = Page("families", "Families & classes", "Families and strength classes", "Does family decide strength?")
    p.nav()
    p.add("class_mix", "hundredPercentStackedBarChart", 16, 68, 676, 300,
          query={"Category": [group], "Y": [proj(meas("Measured grades"))],
                 "Series": [proj(col("grades", "strength_class"), "Strength class")]},
          sort=[(fg, "Ascending")],
          objects={"dataPoint": class_dp, "legend": legend, "labels": props(show=True), "categoryAxis": no_axis_title},
          title="Strength-class mix per family group",
          subtitle="Cast iron holds 22 of the 23 low-strength grades")
    p.add("class_matrix", "pivotTable", 16, 376, 676, 336,
          query={"Rows": [group], "Columns": [proj(col("grades", "strength_class"), "Strength class")],
                 "Values": [proj(meas("Measured grades"))]},
          objects={"values": [{"properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {
              "Input": meas("Measured grades"), "FillRule": {"linearGradient2": {
                  "min": {"color": lit("#FFFFFF")}, "max": {"color": lit("#6AA5EA")},
                  "nullColoringStrategy": {"strategy": lit("asZero")}}}}}}}}},
              "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                           "metadata": "grades.Measured grades"}}]},
          title="Family group × strength class (measured grades)",
          subtitle="The crosstab behind the chi-square test: χ² = 548.7, df = 10, Cramér's V = 0.45")
    p.card("c_high", 700, 68, 278, 96, meas("High-strength share"), "High-strength share (> 600 MPa)")
    p.card("c_measured", 986, 68, 278, 96, meas("Measured grades"), "Grades with measured strength")
    p.add("decomp", "decompositionTreeVisual", 700, 172, 564, 540,
          query={"Analyze": [proj(meas("Measured grades"))],
                 "ExplainBy": [group, proj(col("families", "family_label"), "Family"),
                               proj(col("grades", "product_form"), "Product form"),
                               proj(col("grades", "strength_class"), "Strength class")]},
          title="Drill group → family → form → class", subtitle="Click + on a node and pick the next level")
    pages.append(p)

    # 3 · Carbon is the dial
    p = Page("carbon", "Carbon is the dial", "Carbon is the dial", "What makes a plain steel stronger?")
    p.nav()
    # One row per grade, so the average of a grade's carbon is its carbon (Power BI needs X/Y aggregated here)
    scatter_q = {"Category": [proj(col("grades", "grade_name"), "Grade")],
                 "X": [proj(agg("grades", "carbon_wt", "Avg"), "Carbon (wt %)")],
                 "Y": [proj(agg("grades", "tensile_strength_mpa", "Avg"), "Tensile strength (MPa)")]}
    p.add("carbon_scatter", "scatterChart", 16, 68, 624, 420, query=scatter_q,
          objects={"trend": props(show=True), "dataPoint": props(fill=solid("#2a78d6"))},
          title="Carbon steels: about +43 MPa per 0.1 % C",
          subtitle="Slope 428.6 MPa per wt% C, R² = 0.51 · right-click a point → Drill through → Grade inspector",
          filters=[visual_filter("carbon_only", "grades", "family", ["carbon"])])
    p.add("pooled_scatter", "scatterChart", 648, 68, 616, 420,
          query={**scatter_q, "Series": [group]},
          objects={"dataPoint": group_dp, "legend": legend},
          title="All steels pooled: the trend disappears",
          subtitle="Spearman ρ = −0.03 — alloying, not carbon, sets strength across families (Simpson's paradox)")
    p.add("weld_bands", "clusteredBarChart", 16, 496, 624, 216,
          query={"Category": [proj(col("grades", "weldability_band"), "Weldability")],
                 "Y": [proj(meas("Grades"))]},
          sort=[(col("grades", "weldability_band"), "Descending")],
          objects={"dataPoint": weld_dp, "labels": props(show=True), "categoryAxis": no_axis_title},
          title="Weldability of carbon & low-alloy steels (by carbon equivalent)",
          filters=[visual_filter("weld_na", "grades", "weldability_band", ["Not applicable"], negate=True)])
    p.card("c_weld", 648, 496, 300, 216, meas("Readily weldable share (plain steels)"), "Readily weldable share")
    p.text("carbon_note", 956, 496, 308, 216, [
        ("Reading the page", "11pt", "#1F1F1F", True),
        ("Within plain carbon steels, more carbon means more strength. Pool every family together and the "
         "relationship vanishes, because stainless and tool steels get their strength from alloying elements.",
         "10pt", "#4A4A4A", False),
        ("More carbon also raises the carbon equivalent, so the strongest plain steels are the hardest to weld.",
         "10pt", "#4A4A4A", False)], panel=True)
    pages.append(p)

    # 4 · Chemistry map
    p = Page("chemistry", "Chemistry map", "Chemistry map", "Which steels are chemically alike?")
    p.nav()
    p.add("pca", "scatterChart", 16, 68, 676, 644,
          query={"Category": [proj(col("grades", "grade_name"), "Grade")],
                 "X": [proj(agg("grades", "pc1", "Avg"), "PC1 (15.0 % of variance)")],
                 "Y": [proj(agg("grades", "pc2", "Avg"), "PC2 (11.8 % of variance)")], "Series": [group]},
          objects={"dataPoint": group_dp, "legend": legend},
          title="The chemistry map (PCA of 20 composition features)",
          subtitle="Stainless stretches along PC1, tool steels up PC2, plain steels cluster in the middle")
    elements = ["C", "Mn", "Si", "Cr", "Ni", "Mo", "V", "W", "Co", "Cu"]
    p.add("element_heatmap", "pivotTable", 700, 68, 564, 330,
          query={"Rows": [group], "Columns": [proj(col("elements", "element"), "Element")],
                 "Values": [{**proj(meas("Average wt %"), "Average wt %"), "format": "0.00"}]},
          objects={"values": [{"properties": {"backColor": {"solid": {"color": {"expr": meas("Heatmap colour")}}}},
              "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": "grades.Average wt %"}}],
              "subTotals": props(rowSubtotals=False, columnSubtotals=False)},
          title="Average wt % of key elements by family group",
          subtitle="Shaded per element: the darkest cell is the group that uses that element most",
          filters=[visual_filter("chem_elements", "elements", "element", elements)])
    p.text("chem_note", 700, 406, 564, 306, [
        ("How to read the map", "11pt", "#1F1F1F", True),
        ("Each dot is one grade, placed by its composition: grades close together are chemically alike. The two "
         "axes are the first two principal components of the log-scaled, standardised composition (20 elements "
         "and a trace total).", "10pt", "#4A4A4A", False),
        ("PC1 is driven by chromium and nickel, so stainless grades stretch to the right. PC2 follows tungsten, "
         "vanadium, molybdenum and cobalt, lifting tool and high-speed steels. Cast irons separate on carbon and "
         "silicon.", "10pt", "#4A4A4A", False),
        ("The heatmap above confirms it: Cr and Ni light up for stainless, W, V, Mo and Co for tool steels, C and "
         "Si for cast iron.", "10pt", "#4A4A4A", False)], panel=True)
    pages.append(p)

    # 5 · Grade inspector (drillthrough)
    p = Page("inspector", "Grade inspector", "Grade inspector",
             "What is this one grade? Right-click any grade elsewhere → Drill through → Grade inspector")
    p.visuals[0]["position"]["x"] = 64
    p.add("back", "actionButton", 16, 16, 40, 40,
          objects={"icon": props(shapeType="back")},
          container={"visualLink": props(show=True, type="Back"), "title": props(show=False)})
    p.card("c_name", 16, 68, 1248, 72, agg("grades", "grade_name", "Min"), "Grade")
    for i, (key, field, label) in enumerate([
            ("c_ts", meas("Median strength (MPa)"), "Tensile strength (MPa)"),
            ("c_class", agg("grades", "strength_class", "Min"), "Strength class"),
            ("c_gce", meas("Median carbon equivalent"), "Carbon equivalent"),
            ("c_liq", agg("grades", "liquidus_c", "Min"), "Liquidus (°C)"),
            ("c_weldband", agg("grades", "weldability_band", "Min"), "Weldability")]):
        p.card(key, 16 + i * 251, 148, 243, 88, field, label, font=14 if "Aggregation" in field and key != "c_liq" else None)
    p.add("composition", "clusteredBarChart", 16, 244, 624, 468,
          query={"Category": [proj(col("composition", "element"), "Element")],
                 "Y": [proj(meas("Average wt %"), "wt %")]},
          sort=[(meas("Average wt %"), "Descending")],
          objects={"dataPoint": props(fill=solid("#2a78d6")), "labels": props(show=True)},
          title="Alloying elements (wt %)", subtitle="Iron (the balance) left out",
          filters=[visual_filter("insp_fe", "composition", "element", ["Fe"], negate=True)])
    p.add("details", "tableEx", 648, 244, 616, 120,
          query={"Values": [proj(col("grades", "grade_name"), "Grade"),
                            proj(col("families", "family_label"), "Family"),
                            proj(col("grades", "product_form"), "Form"),
                            proj(col("grades", "designation_standard"), "Standard"),
                            proj(col("grades", "liquidus_is_placeholder"), "Liquidus is placeholder")]},
          objects={"columnWidth": column_widths({
              "grades.grade_name": 250, "families.family_label": 100, "grades.product_form": 50,
              "grades.designation_standard": 70, "grades.liquidus_is_placeholder": 100})},
          title="Identity")
    p.add("comp_table", "tableEx", 648, 372, 616, 340,
          query={"Values": [proj(col("elements", "element"), "Element"),
                            proj(col("elements", "element_name"), "Name"),
                            proj(meas("Average wt %"), "wt %")]},
          sort=[(meas("Average wt %"), "Descending")],
          title="Full composition", subtitle="Every element present, including iron")
    p.page_extra = {
        "type": "Drillthrough", "visibility": "HiddenInViewMode",
        "pageBinding": {"name": uid("binding", "inspector"), "type": "Drillthrough",
                        "parameters": [{"name": uid("param", "inspector"), "boundFilter": uid("filter", "drill"),
                                        "fieldExpr": col("grades", "grade_name")}]},
        "filterConfig": {"filters": [{"name": uid("filter", "drill"), "field": col("grades", "grade_name"),
                                      "type": "Categorical", "howCreated": "Drillthrough"}]}}
    pages.append(p)

    # 6 · Target finder
    p = Page("target", "Target finder", "Target finder", "Which grades meet my requirement?")
    p.nav()
    p.slicer("t_strength", 16, 68, 300, 76, col("grades", "tensile_strength_mpa"), "Tensile strength (MPa)",
             "Between")
    p.slicer("t_liquidus", 324, 68, 300, 76, col("grades", "liquidus_c"), "Liquidus (°C)", "Between")
    p.slicer("t_placeholder", 632, 68, 220, 76, col("grades", "liquidus_is_placeholder"),
             "Liquidus is the 1460 °C placeholder", "Dropdown",
             selected=where("grades", condition("grades", "liquidus_is_placeholder", [False])))
    p.card("t_matches", 860, 68, 404, 76, meas("Measured grades"), "Matching grades")
    p.add("t_families", "clusteredBarChart", 16, 152, 460, 560,
          query={"Category": [group], "Y": [proj(meas("Measured grades"), "Matching grades")]},
          sort=[(meas("Measured grades"), "Descending")],
          objects={"dataPoint": group_dp, "labels": props(show=True), "categoryAxis": no_axis_title},
          title="Which families deliver it?",
          subtitle="Set 800–1200 MPa and 1400–1500 °C for the web app's default target: 94 grades")
    p.add("t_table", "tableEx", 484, 152, 780, 560,
          query={"Values": [proj(col("grades", "grade_name"), "Grade"),
                            proj(col("families", "family_label"), "Family"),
                            proj(col("grades", "product_form"), "Form"),
                            proj(col("grades", "tensile_strength_mpa"), "Strength (MPa)"),
                            proj(col("grades", "liquidus_c"), "Liquidus (°C)"),
                            proj(col("grades", "carbon_equivalent"), "Carbon equivalent")]},
          sort=[(col("grades", "tensile_strength_mpa"), "Descending")],
          objects={"columnWidth": column_widths({
              "grades.grade_name": 255, "families.family_label": 130, "grades.product_form": 70,
              "grades.tensile_strength_mpa": 95, "grades.liquidus_c": 85, "grades.carbon_equivalent": 110})},
          title="Candidate grades", subtitle="Strongest first · right-click a row → Drill through → Grade inspector")
    pages.append(p)
    return pages


def write_report() -> None:
    with open(DATA / "families.csv", encoding="utf-8") as f:
        group_colors = {r["family_group"]: r["group_color"] for r in sorted(csv.DictReader(f),
                                                                           key=lambda r: int(r["group_order"]))}
    pages = build_pages(group_colors)
    defn = REPORT / "definition"
    write_json(REPORT / "definition.pbir", {
        "$schema": SCHEMA + "item/report/definitionProperties/2.0.0/schema.json", "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    write_json(defn / "version.json", {
        "$schema": SCHEMA + "item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    at_import = {"visual": V_VISUAL, "page": V_PAGE, "report": V_REPORT}
    write_json(defn / "report.json", {
        "$schema": f"{SCHEMA}item/report/definition/report/{V_REPORT}/schema.json",
        "themeCollection": {
            "baseTheme": {"name": BASE_THEME, "reportVersionAtImport": at_import, "type": "SharedResources"},
            "customTheme": {"name": f"{NAME}.theme.json", "reportVersionAtImport": at_import,
                            "type": "RegisteredResources"}},
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": BASE_THEME, "path": f"BaseThemes/{BASE_THEME}.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": f"{NAME}.theme.json", "path": f"{NAME}.theme.json", "type": "CustomTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True,
                     "allowChangeFilterTypes": True, "useEnhancedTooltips": True}})
    write_json(defn / "pages" / "pages.json", {
        "$schema": SCHEMA + "item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [p.name for p in pages], "activePageName": pages[0].name})
    for p in pages:
        write_json(defn / "pages" / p.name / "page.json", {
            "$schema": f"{SCHEMA}item/report/definition/page/{V_PAGE}/schema.json", "name": p.name,
            "displayName": p.display, "displayOption": "FitToPage", "height": 720, "width": 1280, **p.page_extra})
        for v in p.visuals:
            write_json(defn / "pages" / p.name / "visuals" / v["name"] / "visual.json", v)

    static = REPORT / "StaticResources"
    (static / "RegisteredResources").mkdir(parents=True, exist_ok=True)
    shutil.copy(PBI / f"{NAME}.theme.json", static / "RegisteredResources" / f"{NAME}.theme.json")
    # The base theme is committed with the report; it is only copied from a Desktop install when missing.
    base = static / "SharedResources" / "BaseThemes" / f"{BASE_THEME}.json"
    if not base.exists():
        source = next((d / THEMES_IN_BIN / base.name for d in desktop_installs()
                       if (d / THEMES_IN_BIN / base.name).exists()), None)
        if source is None:
            raise SystemExit(f"{base.name} not found: install Power BI Desktop or restore {base}")
        base.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, base)
    print(f"report: {len(pages)} pages, {sum(len(p.visuals) for p in pages)} visuals")


def desktop_installs() -> list[Path]:
    """Power BI Desktop folders: the Microsoft Store package (WindowsApps cannot be listed) and the .exe install."""
    found = [Path(r"C:\Program Files\Microsoft Power BI Desktop")]
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "(Get-AppxPackage Microsoft.MicrosoftPowerBIDesktop).InstallLocation"],
                             capture_output=True, text=True, timeout=60).stdout
        found += [Path(line.strip()) for line in out.splitlines() if line.strip()]
    except (OSError, subprocess.SubprocessError):
        pass
    return found


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    for folder in (MODEL / "definition", REPORT / "definition"):
        shutil.rmtree(folder, ignore_errors=True)
    write_model()
    write_report()
    write_json(PBI / f"{NAME}.pbip", {
        "$schema": SCHEMA + "pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
        "artifacts": [{"report": {"path": f"{NAME}.Report"}}], "settings": {"enableAutoRecovery": True}})
    print(f"wrote {PBI / (NAME + '.pbip')}  (DataFolder = {DATA}\\)")


if __name__ == "__main__":
    main()
