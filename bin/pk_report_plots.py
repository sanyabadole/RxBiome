#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Module 5.2 static PK cohort plot generation.")
    parser.add_argument("--cohort-pk-impact", required=True)
    parser.add_argument("--cohort-drug-summary", required=True)
    parser.add_argument("--cohort-sample-summary", required=True)
    parser.add_argument("--drug-plot-output", required=True)
    parser.add_argument("--sample-plot-output", required=True)
    return parser.parse_args()


def _render_cohort_heatmap(cohort_pk: pd.DataFrame, out_path: Path) -> None:
    risk = cohort_pk.loc[:, ["sample_id", "drug_name", "microbiome_impact_factor"]].copy()
    if risk.empty:
        risk = pd.DataFrame({"sample_id": ["NA"], "drug_name": ["NA"], "microbiome_impact_factor": [0.0]})

    pivot = risk.pivot_table(index="sample_id", columns="drug_name", values="microbiome_impact_factor", aggfunc="mean")
    pivot = pivot.fillna(0.0)
    max_val = float(pivot.to_numpy().max()) if not pivot.empty else 1.0
    norm = pivot / max(max_val, 1e-9)

    drug_mean = norm.mean(axis=0).sort_values(ascending=False)

    # ── CI error-bar panel data: mean ± SD of dose-change fraction per drug ─
    ci_col = "recommended_dose_change_fraction"
    if ci_col in cohort_pk.columns and not cohort_pk.empty:
        dose_stats = (
            cohort_pk.groupby("drug_name")[ci_col]
            .agg(mean="mean", std="std")
            .fillna(0)
            .reset_index()
            .sort_values("mean")
        )
    else:
        dose_stats = pd.DataFrame({"drug_name": list(drug_mean.index), "mean": [0.0] * len(drug_mean), "std": [0.0] * len(drug_mean)})

    fig = plt.figure(figsize=(12, 11))
    gs = fig.add_gridspec(3, 1, height_ratios=[4, 1, 1.5], hspace=0.45)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[1, 0])
    ax2 = fig.add_subplot(gs[2, 0])

    sns.heatmap(
        norm,
        ax=ax0,
        cmap="RdYlGn_r",
        vmin=0.0,
        vmax=1.0,
        annot=True,
        fmt=".2f",
        linewidths=0.4,
        linecolor="#eeeeee",
        cbar_kws={"label": "Normalized microbiome PK risk score"},
    )
    ax0.set_title("RxBiome Cohort Drug-Microbiome Risk Heatmap", fontsize=14, pad=12)
    ax0.set_xlabel("Drug")
    ax0.set_ylabel("Sample")

    ax1.bar(drug_mean.index.tolist(), drug_mean.values.tolist(), color="#1f9e89")
    ax1.set_ylim(0.0, 1.0)
    ax1.set_ylabel("Mean risk")
    ax1.set_title("Mean Risk Score by Drug", fontsize=11)
    ax1.tick_params(axis="x", rotation=20)

    # ── CI panel: horizontal error bars (mean ± 1 SD dose change) ─────────
    ax2.errorbar(
        dose_stats["mean"],
        dose_stats["drug_name"],
        xerr=dose_stats["std"],
        fmt="o",
        color="#01696f",      # teal mean point
        ecolor="#888888",     # gray CI whiskers
        capsize=4,
        markersize=7,
        linewidth=1.5,
    )
    ax2.axvline(0, color="#dddddd", linestyle="--", linewidth=0.8)
    ax2.set_xlabel("Mean Dose Change ± SD (fraction)")
    ax2.set_title("Dose Change Uncertainty (Mean ± 1 SD)", fontsize=11)
    ax2.tick_params(axis="y", labelsize=9)

    fig.savefig(out_path, format="svg", bbox_inches="tight")
    plt.close(fig)


def _risk_label(value: float) -> str:
    if value >= 0.7:
        return "High"
    if value >= 0.4:
        return "Medium"
    return "Low"


def _render_patient_dashboard(cohort_pk: pd.DataFrame, sample_summary: pd.DataFrame, out_path: Path) -> None:
    if cohort_pk.empty:
        cohort_pk = pd.DataFrame(
            {
                "sample_id": ["NA"],
                "drug_name": ["NA"],
                "dominant_species": ["NA"],
                "microbiome_impact_factor": [0.0],
            }
        )
    if sample_summary.empty:
        focus_sample = str(cohort_pk["sample_id"].iloc[0])
    else:
        focus_sample = (
            sample_summary.sort_values("max_abs_recommended_dose_change_fraction", ascending=False)["sample_id"].iloc[0]
        )

    sample_rows = cohort_pk[cohort_pk["sample_id"] == focus_sample].copy()
    if sample_rows.empty:
        sample_rows = cohort_pk.copy()
        focus_sample = str(sample_rows["sample_id"].iloc[0])

    max_val = float(cohort_pk["microbiome_impact_factor"].max()) if "microbiome_impact_factor" in cohort_pk else 1.0
    max_val = max(max_val, 1e-9)
    sample_rows["risk_norm"] = sample_rows["microbiome_impact_factor"] / max_val
    sample_rows["risk_level"] = sample_rows["risk_norm"].apply(_risk_label)
    sample_rows["confidence_pct"] = (sample_rows["risk_norm"] * 100.0).clip(lower=1.0, upper=99.0).round(0).astype(int)
    scorecard = sample_rows.sort_values("risk_norm", ascending=False).head(8)

    fig = plt.figure(figsize=(14, 8))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.6, 1.0], height_ratios=[1.0, 1.0], wspace=0.3, hspace=0.35)
    ax_table = fig.add_subplot(gs[:, 0])
    ax_bar = fig.add_subplot(gs[0, 1])
    ax_donut = fig.add_subplot(gs[1, 1])

    ax_table.axis("off")
    table_df = scorecard.loc[:, ["drug_name", "risk_level", "dominant_species", "confidence_pct"]].copy()
    table_df.columns = ["Drug", "Risk", "Predicted organism", "Confidence %"]
    tbl = ax_table.table(
        cellText=table_df.values,
        colLabels=table_df.columns,
        loc="center",
        cellLoc="left",
        colLoc="left",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1, 1.6)
    ax_table.set_title(f"RxBiome Patient Drug-Microbiome Risk Scorecard ({focus_sample})", fontsize=14, pad=10)

    top_species = (
        scorecard.groupby("dominant_species", as_index=False)["risk_norm"].sum().sort_values("risk_norm", ascending=False).head(6)
    )
    ax_bar.barh(top_species["dominant_species"], top_species["risk_norm"], color="#5E60CE")
    ax_bar.invert_yaxis()
    ax_bar.set_xlim(0.0, 1.0)
    ax_bar.set_xlabel("Relative abundance proxy")
    ax_bar.set_title("Drug-Metabolizing Organism Abundance")

    risk_counts = scorecard["risk_level"].value_counts()
    ordered = [risk_counts.get("High", 0), risk_counts.get("Medium", 0), risk_counts.get("Low", 0)]
    labels = ["High", "Medium", "Low"]
    colors = ["#d62828", "#fcbf49", "#2a9d8f"]
    ax_donut.pie(
        ordered,
        labels=labels,
        colors=colors,
        startangle=90,
        wedgeprops={"width": 0.45, "edgecolor": "white"},
        autopct="%1.0f%%",
    )
    ax_donut.set_title("Microbiome Risk Distribution")
    fig.savefig(out_path, format="svg", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    args = parse_args()
    cohort_pk = pd.read_csv(args.cohort_pk_impact, sep="\t")
    drug = pd.read_csv(args.cohort_drug_summary, sep="\t")
    sample = pd.read_csv(args.cohort_sample_summary, sep="\t")
    _ = drug  # kept for future extensions; current rendering consumes cohort + sample summaries.
    _render_cohort_heatmap(cohort_pk=cohort_pk, out_path=Path(args.drug_plot_output))
    _render_patient_dashboard(cohort_pk=cohort_pk, sample_summary=sample, out_path=Path(args.sample_plot_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
