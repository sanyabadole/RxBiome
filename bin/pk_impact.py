#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

# Ensure sibling model file is importable when executed from task PATH.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pk_impact_models import PKConfig, empty_pk_output, load_interactions, load_pk_metadata, validate_pk_output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic Module 4 PK impact calculator.")
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--interactions", required=True, help="Module 3 interactions TSV")
    parser.add_argument("--drug-pk-metadata", required=True, help="Optional drug PK metadata CSV")
    parser.add_argument("--target-exposure-multiplier", type=float, default=1.0)
    parser.add_argument("--max-dose-adjustment-fraction", type=float, default=0.5)
    parser.add_argument("--min-confidence-interval-width", type=float, default=0.1)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _tier_from_uncertainty(ci_width: float, abs_change_fraction: float) -> str:
    if ci_width <= 0.20 and abs_change_fraction >= 0.20:
        return "HIGH"
    if ci_width <= 0.40 and abs_change_fraction >= 0.10:
        return "MEDIUM"
    return "LOW"


def compute_pk_impact(interactions: pd.DataFrame, metadata: pd.DataFrame, cfg: PKConfig, sample_id: str) -> pd.DataFrame:
    if interactions.empty:
        return empty_pk_output()

    # Pick dominant species as the top interaction contributor per sample+drug.
    top_species = (
        interactions.sort_values("interaction_confidence", ascending=False)
        .drop_duplicates(subset=["sample_id", "drug_name", "drugbank_id"], keep="first")
        .loc[:, ["sample_id", "drug_name", "drugbank_id", "species"]]
        .rename(columns={"species": "dominant_species"})
    )

    grp = (
        interactions.groupby(["sample_id", "drug_name", "drugbank_id"], as_index=False)
        .agg(
            microbiome_impact_factor=("interaction_confidence", "mean"),
        )
    )
    grp = grp.merge(top_species, on=["sample_id", "drug_name", "drugbank_id"], how="left")

    sample_df = grp[grp["sample_id"] == sample_id].copy()
    if sample_df.empty:
        return empty_pk_output()

    meta_keep = metadata.drop_duplicates(subset=["drug_name", "drugbank_id"]).copy()
    merged = sample_df.merge(meta_keep, on=["drug_name", "drugbank_id"], how="left")
    merged["standard_dose_mg"] = merged["standard_dose_mg"].fillna(100.0)

    # Smoothly map arbitrary interaction scales onto [0,1] without hard clipping.
    mif_scaled = (1.0 - np.exp(-merged["microbiome_impact_factor"].astype(float) / 20.0)).clip(0.0, 1.0)
    clearance_multiplier = (1.0 + (mif_scaled - 0.5) * 0.6).clip(0.7, 1.3)
    auc_multiplier = (1.0 / clearance_multiplier).clip(0.7, 1.4)

    desired_dose = merged["standard_dose_mg"] * (cfg.target_exposure_multiplier / auc_multiplier)
    raw_change_fraction = (desired_dose / merged["standard_dose_mg"]) - 1.0
    clipped_change_fraction = raw_change_fraction.clip(
        lower=-cfg.max_dose_adjustment_fraction,
        upper=cfg.max_dose_adjustment_fraction,
    )
    recommended_dose = merged["standard_dose_mg"] * (1.0 + clipped_change_fraction)

    base_uncertainty = (1.0 - mif_scaled) * 0.35 + 0.05
    ci_half_width = np.maximum(cfg.min_confidence_interval_width / 2.0, base_uncertainty / 2.0)
    confidence_low = (recommended_dose * (1.0 - ci_half_width)).clip(lower=0.0)
    confidence_high = recommended_dose * (1.0 + ci_half_width)
    ci_width_fraction = (confidence_high - confidence_low) / recommended_dose.replace(0, np.nan)
    ci_width_fraction = ci_width_fraction.fillna(1.0)

    abs_change_fraction = clipped_change_fraction.abs()
    risk_tier = [
        _tier_from_uncertainty(ci_w, delta) for ci_w, delta in zip(ci_width_fraction, abs_change_fraction, strict=False)
    ]

    out = pd.DataFrame(
        {
            "sample_id": merged["sample_id"],
            "drug_name": merged["drug_name"],
            "drugbank_id": merged["drugbank_id"],
            "standard_dose_mg": merged["standard_dose_mg"],
            "microbiome_impact_factor": merged["microbiome_impact_factor"],
            "predicted_clearance_multiplier": clearance_multiplier,
            "predicted_auc_multiplier": auc_multiplier,
            "recommended_dose_mg": recommended_dose,
            "recommended_dose_change_fraction": clipped_change_fraction,
            "confidence_low": confidence_low,
            "confidence_high": confidence_high,
            "pk_risk_tier": risk_tier,
            "dominant_species": merged["dominant_species"],
            "mechanistic_note": "Dose adjusted from microbiome interaction burden and bounded by max adjustment policy.",
        }
    )
    return out


def main() -> int:
    args = parse_args()
    cfg = PKConfig(
        target_exposure_multiplier=args.target_exposure_multiplier,
        max_dose_adjustment_fraction=args.max_dose_adjustment_fraction,
        min_confidence_interval_width=args.min_confidence_interval_width,
    )

    interactions = load_interactions(args.interactions)
    metadata_path = Path(args.drug_pk_metadata)
    metadata = load_pk_metadata(metadata_path) if metadata_path.exists() else pd.DataFrame()
    if metadata.empty:
        metadata = pd.DataFrame(columns=["drug_name", "drugbank_id", "standard_dose_mg"])

    out = compute_pk_impact(interactions=interactions, metadata=metadata, cfg=cfg, sample_id=args.sample_id)
    validate_pk_output(out)
    out.to_csv(args.output, sep="\t", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
