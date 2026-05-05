#!/usr/bin/env python3

"""
Module 4 (PK impact) data contracts and validators.

This file defines strict input/output schemas for:
1) Module 3 interaction tables
2) Optional drug PK metadata table
3) Module 4 PK impact output table

Later Module 4 compute code should import and reuse these helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


INTERACTION_REQUIRED_COLUMNS = {
    "sample_id",
    "drug_name",
    "drugbank_id",
    "drug_class",
    "species",
    "taxonomic_confidence",
    "microberx_score",
    "pathway_coverage_weight",
    "interaction_confidence",
    "risk_tier",
}

PK_METADATA_REQUIRED_COLUMNS = {
    "drug_name",
    "drugbank_id",
}

PK_OUTPUT_COLUMNS = [
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


@dataclass(frozen=True)
class PKConfig:
    # Dose/exposure targets
    target_exposure_multiplier: float = 1.0
    max_dose_adjustment_fraction: float = 0.5
    min_confidence_interval_width: float = 0.1
    # MIF scaling (Task 1 / Task 5)
    mif_scale_factor: float = 0.5          # divisor in 1-exp(-MIF/scale); 0.5 for 0-1 range, 20 for legacy 0-100
    # Clearance/AUC clip bounds (Task 5)
    clearance_clip_min: float = 0.7
    clearance_clip_max: float = 1.3
    auc_clip_min: float = 0.7
    auc_clip_max: float = 1.4
    # Confidence interval shape (Task 5)
    ci_base_uncertainty_scale: float = 0.35   # coefficient: width = (1-mif_scaled)*this + offset
    ci_min_offset: float = 0.05               # minimum CI half-width offset


def _ensure_columns(df: pd.DataFrame, required: set[str], table_name: str) -> None:
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"{table_name} missing required columns: {missing}")


def _as_numeric(df: pd.DataFrame, columns: Iterable[str], table_name: str) -> None:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if df[col].isna().any():
                raise ValueError(f"{table_name} has non-numeric values in column: {col}")


def load_interactions(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    _ensure_columns(df, INTERACTION_REQUIRED_COLUMNS, "interactions TSV")
    _as_numeric(
        df,
        ["microberx_score", "pathway_coverage_weight", "interaction_confidence"],
        "interactions TSV",
    )
    return df


def load_pk_metadata(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    _ensure_columns(df, PK_METADATA_REQUIRED_COLUMNS, "drug PK metadata CSV")
    _as_numeric(df, ["standard_dose_mg", "target_auc", "bioavailability_fraction"], "drug PK metadata CSV")
    return df


def empty_pk_output() -> pd.DataFrame:
    return pd.DataFrame(columns=PK_OUTPUT_COLUMNS)


def validate_pk_output(df: pd.DataFrame) -> None:
    _ensure_columns(df, set(PK_OUTPUT_COLUMNS), "pk impact output")
    _as_numeric(
        df,
        [
            "standard_dose_mg",
            "microbiome_impact_factor",
            "predicted_clearance_multiplier",
            "predicted_auc_multiplier",
            "recommended_dose_mg",
            "recommended_dose_change_fraction",
            "confidence_low",
            "confidence_high",
        ],
        "pk impact output",
    )
    if (df["confidence_high"] < df["confidence_low"]).any():
        raise ValueError("pk impact output has confidence_high < confidence_low")


if __name__ == "__main__":
    # Small self-check for local development.
    print("pk_impact_models loaded; contracts ready.")
