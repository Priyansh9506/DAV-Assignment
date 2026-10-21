// SteelScope Power Query (M). One block per query.
// Home → Transform data → Home → New Source → Blank Query → Advanced Editor → paste the block → rename the query
// to the name in its header comment. Create the DataFolder parameter first.

// ===== Parameter: DataFolder =====
// Home → Manage Parameters → New: Name = DataFolder, Type = Text, Current value = the full path of powerbi\data\
// WITH the trailing backslash, e.g.  D:\B.Tech\Sem - 5\DAV\Innovative Assignment\Project\powerbi\data\

// ===== Query: grades =====
let
    Source = Csv.Document(File.Contents(DataFolder & "grades.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {
            {"grade_id", type text}, {"grade_name", type text}, {"family", type text}, {"product_form", type text},
            {"designation_standard", type text}, {"tensile_strength_mpa", type number},
            {"has_measured_strength", type logical}, {"strength_class", type text}, {"strength_class_order", Int64.Type},
            {"liquidus_c", type number}, {"liquidus_is_placeholder", type logical}, {"carbon_equivalent", type number},
            {"alloying_total_wt", type number}, {"cr_equivalent", type number}, {"ni_equivalent", type number},
            {"carbon_wt", type number}, {"chromium_wt", type number}, {"nickel_wt", type number},
            {"molybdenum_wt", type number}, {"pc1", type number}, {"pc2", type number}, {"weldability_band", type text}
        },
        "en-US"
    )
in
    Typed

// ===== Query: composition =====
let
    Source = Csv.Document(File.Contents(DataFolder & "composition.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"grade_id", type text}, {"element", type text}, {"wt_pct", type number}}, "en-US")
in
    Typed

// ===== Query: families =====
let
    Source = Csv.Document(File.Contents(DataFolder & "families.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {{"family", type text}, {"family_label", type text}, {"family_group", type text}, {"group_order", Int64.Type}, {"group_color", type text}},
        "en-US"
    )
in
    Typed

// ===== Query: elements =====
let
    Source = Csv.Document(File.Contents(DataFolder & "elements.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"element", type text}, {"element_name", type text}, {"is_rare_trace", type logical}}, "en-US")
in
    Typed
