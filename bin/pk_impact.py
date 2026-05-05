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
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--dose-plot-output", required=True)
    parser.add_argument("--risk-plot-output", required=True)
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


def build_sample_summary(pk: pd.DataFrame) -> pd.DataFrame:
    if pk.empty:
        return pd.DataFrame(
            [
                {
                    "sample_id": "",
                    "n_drugs": 0,
                    "mean_dose_change_fraction": 0.0,
                    "max_abs_dose_change_fraction": 0.0,
                    "n_high_risk": 0,
                    "n_medium_risk": 0,
                    "n_low_risk": 0,
                }
            ]
        )

    sample_id = str(pk["sample_id"].iloc[0])
    risk_counts = pk["pk_risk_tier"].value_counts().to_dict()
    return pd.DataFrame(
        [
            {
                "sample_id": sample_id,
                "n_drugs": int(len(pk)),
                "mean_dose_change_fraction": float(pk["recommended_dose_change_fraction"].mean()),
                "max_abs_dose_change_fraction": float(pk["recommended_dose_change_fraction"].abs().max()),
                "n_high_risk": int(risk_counts.get("HIGH", 0)),
                "n_medium_risk": int(risk_counts.get("MEDIUM", 0)),
                "n_low_risk": int(risk_counts.get("LOW", 0)),
            }
        ]
    )


def _write_bar_svg(labels: list[str], values: list[float], title: str, y_label: str, out_path: Path) -> None:
    width, height = 800, 420
    left, right, top, bottom = 80, 20, 60, 100
    plot_w, plot_h = width - left - right, height - top - bottom
    max_val = max(values) if values else 1.0
    max_val = max(max_val, 1e-9)
    bar_gap = 20
    n = max(len(values), 1)
    bar_w = max((plot_w - (n - 1) * bar_gap) / n, 20)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'<text x="{width/2}" y="30" text-anchor="middle" font-size="20" font-family="Arial">{title}</text>',
        f'<text x="18" y="{top + plot_h/2}" transform="rotate(-90 18,{top + plot_h/2})" text-anchor="middle" font-size="12" font-family="Arial">{y_label}</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#333" stroke-width="2"/>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#333" stroke-width="2"/>',
    ]

    for i, (label, value) in enumerate(zip(labels, values, strict=False)):
        x = left + i * (bar_w + bar_gap)
        h = (value / max_val) * (plot_h * 0.9)
        y = top + plot_h - h
        lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="#4C78A8"/>')
        lines.append(f'<text x="{x + bar_w/2:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-size="10" font-family="Arial">{value:.3f}</text>')
        lines.append(f'<text x="{x + bar_w/2:.1f}" y="{top + plot_h + 18}" text-anchor="middle" font-size="10" font-family="Arial">{label}</text>')

    lines.append("</svg>")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_reports(pk: pd.DataFrame, summary_out: Path, dose_plot_out: Path, risk_plot_out: Path) -> None:
    summary = build_sample_summary(pk)
    summary.to_csv(summary_out, sep="\t", index=False)

    dose_df = pk.loc[:, ["drug_name", "recommended_dose_change_fraction"]].copy()
    _write_bar_svg(
        labels=[str(x) for x in dose_df["drug_name"].tolist()],
        values=[float(x) for x in dose_df["recommended_dose_change_fraction"].abs().tolist()],
        title="Absolute Dose Change Fraction by Drug",
        y_label="abs(dose_change_fraction)",
        out_path=dose_plot_out,
    )

    risk_counts = pk["pk_risk_tier"].value_counts().reindex(["HIGH", "MEDIUM", "LOW"], fill_value=0)
    _write_bar_svg(
        labels=[str(x) for x in risk_counts.index.tolist()],
        values=[float(x) for x in risk_counts.tolist()],
        title="PK Risk Tier Counts",
        y_label="count",
        out_path=risk_plot_out,
    )


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
    write_reports(
        pk=out,
        summary_out=Path(args.summary_output),
        dose_plot_out=Path(args.dose_plot_output),
        risk_plot_out=Path(args.risk_plot_output),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
