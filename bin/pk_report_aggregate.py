#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Module 5.1 cohort-level PK report aggregation.")
    parser.add_argument(
        "--pk-impact-files",
        nargs="+",
        required=True,
        help="One or more per-sample *.pk_impact.tsv files from Module 4.",
    )
    parser.add_argument("--cohort-pk-impact-output", required=True)
    parser.add_argument("--cohort-drug-summary-output", required=True)
    parser.add_argument("--cohort-sample-summary-output", required=True)
    return parser.parse_args()


def load_pk_impact_tables(paths: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for p in paths:
        df = pd.read_csv(p, sep="\t")
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=0, ignore_index=True)


def build_drug_summary(cohort: pd.DataFrame) -> pd.DataFrame:
    if cohort.empty:
        return pd.DataFrame(
            columns=[
                "drug_name",
                "drugbank_id",
                "n_samples",
                "mean_recommended_dose_change_fraction",
                "mean_predicted_auc_multiplier",
                "high_risk_count",
                "medium_risk_count",
                "low_risk_count",
            ]
        )

    base = (
        cohort.groupby(["drug_name", "drugbank_id"], as_index=False)
        .agg(
            n_samples=("sample_id", "nunique"),
            mean_recommended_dose_change_fraction=("recommended_dose_change_fraction", "mean"),
            mean_predicted_auc_multiplier=("predicted_auc_multiplier", "mean"),
        )
    )

    tier = (
        cohort.groupby(["drug_name", "drugbank_id", "pk_risk_tier"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .pivot(index=["drug_name", "drugbank_id"], columns="pk_risk_tier", values="count")
        .fillna(0)
        .reset_index()
    )

    for tier_name in ["HIGH", "MEDIUM", "LOW"]:
        if tier_name not in tier.columns:
            tier[tier_name] = 0

    tier = tier.rename(
        columns={
            "HIGH": "high_risk_count",
            "MEDIUM": "medium_risk_count",
            "LOW": "low_risk_count",
        }
    )

    out = base.merge(tier, on=["drug_name", "drugbank_id"], how="left")
    return out.sort_values(["mean_recommended_dose_change_fraction", "drug_name"], ascending=[False, True])


def build_sample_summary(cohort: pd.DataFrame) -> pd.DataFrame:
    if cohort.empty:
        return pd.DataFrame(
            columns=[
                "sample_id",
                "n_drugs",
                "mean_recommended_dose_change_fraction",
                "max_abs_recommended_dose_change_fraction",
                "high_risk_count",
                "medium_risk_count",
                "low_risk_count",
            ]
        )

    base = (
        cohort.groupby("sample_id", as_index=False)
        .agg(
            n_drugs=("drug_name", "nunique"),
            mean_recommended_dose_change_fraction=("recommended_dose_change_fraction", "mean"),
            max_abs_recommended_dose_change_fraction=("recommended_dose_change_fraction", lambda s: s.abs().max()),
        )
    )

    tier = (
        cohort.groupby(["sample_id", "pk_risk_tier"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .pivot(index="sample_id", columns="pk_risk_tier", values="count")
        .fillna(0)
        .reset_index()
    )

    for tier_name in ["HIGH", "MEDIUM", "LOW"]:
        if tier_name not in tier.columns:
            tier[tier_name] = 0

    tier = tier.rename(
        columns={
            "HIGH": "high_risk_count",
            "MEDIUM": "medium_risk_count",
            "LOW": "low_risk_count",
        }
    )

    out = base.merge(tier, on="sample_id", how="left")
    return out.sort_values("sample_id")


def main() -> int:
    args = parse_args()
    cohort = load_pk_impact_tables(args.pk_impact_files)

    if cohort.empty:
        cohort = pd.DataFrame(
            columns=[
                "sample_id",
                "drug_name",
                "drugbank_id",
                "standard_dose_mg",
                "microbiome_impact_factor",
                "predicted_clearance_multiplier",
                "predicted_auc_multiplier",
                "recommended_dose_mg",
                "recommended_dose_change_fraction",
                "confidence_low",
                "confidence_high",
                "pk_risk_tier",
                "dominant_species",
                "mechanistic_note",
            ]
        )

    drug_summary = build_drug_summary(cohort)
    sample_summary = build_sample_summary(cohort)

    cohort.to_csv(Path(args.cohort_pk_impact_output), sep="\t", index=False)
    drug_summary.to_csv(Path(args.cohort_drug_summary_output), sep="\t", index=False)
    sample_summary.to_csv(Path(args.cohort_sample_summary_output), sep="\t", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
