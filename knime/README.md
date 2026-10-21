# KNIME

Everything for the KNIME part of the project: the statistics workflow, the machine learning and the dashboard.

```
knime/
├── KNIME_GUIDE.md                    ← every node's settings and the value it should produce
├── KNIME_WORKFLOW_STEP_BY_STEP.md    ← click-by-click build sheet: wiring map, build order, checkpoints
├── workflow/
│   └── SteelScope_Visual_Analytics.knwf   ← the finished workflow
├── data/                             ← CSVs written by notebook 03 (never edit by hand)
│   ├── knime_input.csv                   1,389 grades with a group-safe train/test split column
│   └── viz_expected_values.csv           every statistic the workflow should reproduce
└── python_views/                     ← scripts to paste into KNIME Python View nodes
```

## Open the workflow

1. KNIME Analytics Platform 5.x: *File → Import KNIME Workflow…* → `workflow/SteelScope_Visual_Analytics.knwf`.
2. The workflow reads `knime_input.csv` from its own workflow data area, so no path needs changing.
3. Python View nodes need the **KNIME Python Integration** with the **Bundled** environment
   (*Preferences → KNIME → Python*).
4. **Execute all** (Shift + F7).

## Machine-learning results (265 unseen test grades)

| Model | Result | Baseline |
|---|---|---|
| k-NN (k = 5, Min-Max scaled) | accuracy 0.842, Cohen's κ ≈ 0.70 | always "high": 0.502 |
| Random forest (regression of tensile strength) | R² 0.731, MAE 66.5 MPa, RMSE 95.8 MPa | predict the mean: MAE 134.4 MPa |

Tensile strength is removed from the classifiers' inputs (Column Filter) because the strength class is defined
from it; `strength_class` is excluded from the random forest for the same reason.
