#!/usr/bin/env python3
"""
Module 5.3 — Markdown cohort PK report renderer.

Produces cohort.pk_report.md from the aggregated tables and plot paths.
Now includes a "Cohort Statistical Summary" section with per-drug AUC
statistics, dominant-species frequency, and an optional QC/filter note.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Module 5.3 Markdown report renderer for cohort PK outputs.")
    parser.add_argument("--cohort-pk-impact",     required=True,  help="cohort.pk_impact.tsv from M5.1")
    parser.add_argument("--cohort-drug-summary",  required=True)
    parser.add_argument("--cohort-sample-summary", required=True)
    parser.add_argument("--cohort-drug-plot",     required=True)
    parser.add_argument("--cohort-sample-plot",   required=True)
    parser.add_argument("--output",               required=True)
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fmt_table(df: pd.DataFrame, max_rows: int = 10) -> str:
    """Render a DataFrame as a Markdown table string."""
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


def _build_drug_stats_table(cohort_pk: pd.DataFrame) -> str:
    """
    Per-drug statistics: mean/std AUC shift, dose range, tier percentages.
    Columns: drug_name | n_samples | mean_auc_shift | std_auc_shift |
             dose_range_mg | pct_high | pct_medium | pct_low
    """
    if cohort_pk.empty:
        return "_No data available._"

    stats = (
        cohort_pk.groupby(["drug_name", "drugbank_id"])
        .agg(
            n_samples=("sample_id", "nunique"),
            mean_auc_shift=("predicted_auc_multiplier", lambda x: (x - 1.0).mean()),
            std_auc_shift=("predicted_auc_multiplier", lambda x: (x - 1.0).std()),
            min_dose=("recommended_dose_mg", "min"),
            max_dose=("recommended_dose_mg", "max"),
        )
        .reset_index()
    )

    # Tier percentages per drug
    tier_raw = (
        cohort_pk.groupby(["drug_name", "drugbank_id", "pk_risk_tier"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    tier_pivot = (
        tier_raw.pivot(index=["drug_name", "drugbank_id"], columns="pk_risk_tier", values="count")
        .fillna(0)
        .reset_index()
    )
    for tier in ("HIGH", "MEDIUM", "LOW"):
        if tier not in tier_pivot.columns:
            tier_pivot[tier] = 0
    tier_pivot["_total"] = tier_pivot[["HIGH", "MEDIUM", "LOW"]].sum(axis=1).replace(0, 1)
    tier_pivot["pct_high"]   = (tier_pivot["HIGH"]   / tier_pivot["_total"] * 100).round(1)
    tier_pivot["pct_medium"] = (tier_pivot["MEDIUM"] / tier_pivot["_total"] * 100).round(1)
    tier_pivot["pct_low"]    = (tier_pivot["LOW"]    / tier_pivot["_total"] * 100).round(1)

    merged = stats.merge(
        tier_pivot[["drug_name", "drugbank_id", "pct_high", "pct_medium", "pct_low"]],
        on=["drug_name", "drugbank_id"],
        how="left",
    )

    display = merged.copy()
    display["mean_auc_shift"] = display["mean_auc_shift"].apply(
        lambda v: f"{v:+.4f}" if pd.notna(v) else "—"
    )
    display["std_auc_shift"] = display["std_auc_shift"].apply(
        lambda v: f"{v:.4f}" if pd.notna(v) else "—"
    )
    display["dose_range_mg"] = display.apply(
        lambda r: f"{r['min_dose']:.0f}–{r['max_dose']:.0f} mg", axis=1
    )

    result_df = display[[
        "drug_name", "n_samples", "mean_auc_shift", "std_auc_shift",
        "dose_range_mg", "pct_high", "pct_medium", "pct_low",
    ]].copy()
    return _fmt_table(result_df, max_rows=20)


def _build_dominant_species_list(cohort_pk: pd.DataFrame, top_n: int = 5) -> str:
    """
    Top-5 dominant species by frequency among HIGH-risk interactions.
    Falls back to all-tier counts when no HIGH-risk rows exist.
    """
    if cohort_pk.empty or "dominant_species" not in cohort_pk.columns:
        return "_No species data available._"

    high_risk = cohort_pk[cohort_pk["pk_risk_tier"] == "HIGH"]
    if not high_risk.empty:
        total_high = max(len(high_risk), 1)
        counts = high_risk["dominant_species"].value_counts().head(top_n)
        lines = []
        for i, (sp, cnt) in enumerate(counts.items(), 1):
            pct = round(cnt / total_high * 100)
            lines.append(f"{i}. *{sp}* — drives {pct}% of HIGH-risk interactions")
        return "\n".join(lines)

    # Fall back to all interactions
    total = max(len(cohort_pk), 1)
    counts = cohort_pk["dominant_species"].value_counts().head(top_n)
    lines = []
    for i, (sp, cnt) in enumerate(counts.items(), 1):
        pct = round(cnt / total * 100)
        lines.append(f"{i}. *{sp}* — drives {pct}% of all interactions (no HIGH-risk tier present)")
    return "\n".join(lines)


def _build_qc_note(cohort_pk: pd.DataFrame) -> str | None:
    """
    Return a QC note block if any samples appear to have used the fallback
    standard dose (500 mg), indicating missing drug PK metadata for those
    drugs. Returns None when no fallback usage is detected.
    """
    if cohort_pk.empty or "standard_dose_mg" not in cohort_pk.columns:
        return None
    fallback_rows = cohort_pk[cohort_pk["standard_dose_mg"] == 500.0]
    if fallback_rows.empty:
        return None
    affected = sorted(fallback_rows["sample_id"].unique())
    n = len(affected)
    ids = ", ".join(affected)
    return (
        f"> ⚠️ **QC Note:** {n} sample(s) had one or more drugs with missing PK metadata "
        f"(fallback standard_dose=500 mg applied): {ids}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()

    cohort_pk = pd.read_csv(args.cohort_pk_impact, sep="\t", comment="#")
    drug      = pd.read_csv(args.cohort_drug_summary, sep="\t")
    sample    = pd.read_csv(args.cohort_sample_summary, sep="\t")

    output_path = Path(args.output)

    lines: list[str] = [
        "# RxBiome Module 5 Cohort PK Report",
        "",
        "## Overview",
        f"- Drugs in cohort summary: **{len(drug)}**",
        f"- Samples in cohort summary: **{len(sample)}**",
        "",
    ]

    # ── NEW: Cohort Statistical Summary ───────────────────────────────────
    lines += [
        "## Cohort Statistical Summary",
        "",
        "### Per-Drug AUC Shift and Risk Statistics",
        "",
        _build_drug_stats_table(cohort_pk),
        "",
        "### Most Influential Organisms (Cohort-Wide)",
        "",
        _build_dominant_species_list(cohort_pk),
        "",
    ]

    # Optional QC/filter note
    qc_note = _build_qc_note(cohort_pk)
    if qc_note is not None:
        lines += [qc_note, ""]

    # ── Existing sections ─────────────────────────────────────────────────
    lines += [
        "## Cohort Drug Summary (Top 10 by mean dose-change fraction)",
        _fmt_table(
            drug.sort_values("mean_recommended_dose_change_fraction", ascending=False),
            max_rows=10,
        ),
        "",
        "## Cohort Sample Summary",
        _fmt_table(
            sample.sort_values("max_abs_recommended_dose_change_fraction", ascending=False),
            max_rows=20,
        ),
        "",
        "## Plots",
        f"![Drug dose change plot]({Path(args.cohort_drug_plot).name})",
        "",
        f"![Sample max dose change plot]({Path(args.cohort_sample_plot).name})",
        "",
        "## Interpretation Notes",
        "- Larger absolute dose-change fractions indicate stronger microbiome-linked exposure shift under the current deterministic model.",
        "- High/Medium/Low counts summarize model-derived PK risk tiers, not clinical decision labels.",
        "- `mean_auc_shift` = mean(predicted_auc_multiplier − 1.0); positive values indicate increased systemic exposure.",
    ]

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
