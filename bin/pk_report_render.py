#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Module 5.3 Markdown report renderer for cohort PK outputs.")
    parser.add_argument("--cohort-drug-summary", required=True)
    parser.add_argument("--cohort-sample-summary", required=True)
    parser.add_argument("--cohort-drug-plot", required=True)
    parser.add_argument("--cohort-sample-plot", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _fmt_table(df: pd.DataFrame, max_rows: int = 10) -> str:
    if df.empty:
        return "_No rows available._"
    head = df.head(max_rows).copy()
    cols = [str(c) for c in head.columns.tolist()]
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for row in head.itertuples(index=False, name=None):
        vals = [str(v) for v in row]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    drug = pd.read_csv(args.cohort_drug_summary, sep="\t")
    sample = pd.read_csv(args.cohort_sample_summary, sep="\t")

    output_path = Path(args.output)
    lines = [
        "# RxBiome Module 5 Cohort PK Report",
        "",
        "## Overview",
        f"- Drugs in cohort summary: **{len(drug)}**",
        f"- Samples in cohort summary: **{len(sample)}**",
        "",
        "## Cohort Drug Summary (Top 10 by mean dose-change fraction)",
        _fmt_table(drug.sort_values("mean_recommended_dose_change_fraction", ascending=False), max_rows=10),
        "",
        "## Cohort Sample Summary",
        _fmt_table(sample.sort_values("max_abs_recommended_dose_change_fraction", ascending=False), max_rows=20),
        "",
        "## Plots",
        f"![Drug dose change plot]({Path(args.cohort_drug_plot).name})",
        "",
        f"![Sample max dose change plot]({Path(args.cohort_sample_plot).name})",
        "",
        "## Interpretation Notes",
        "- Larger absolute dose-change fractions indicate stronger microbiome-linked exposure shift under the current deterministic model.",
        "- High/Medium/Low counts summarize model-derived PK risk tiers, not clinical decision labels.",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
