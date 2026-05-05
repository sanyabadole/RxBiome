"""
Unit tests for Module 4 PK impact logic.

Covers:
  2a. MIF scale factor formula (the critical saturation fix)
  2b. compute_pk_impact() with known MIF values
  2c. Risk tier boundary conditions
  2d. load_interactions() edge cases
  2e. SVG output smoke test (subprocess)
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# conftest.py already adds bin/ to sys.path; these imports work directly.
from pk_impact import _tier_from_uncertainty, compute_pk_impact, write_reports
from pk_impact_models import PKConfig, load_interactions


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_interactions_df() -> pd.DataFrame:
    """
    Small valid interactions DataFrame with 2 drugs and ≥3 rows each.
    Suitable as reusable input across multiple test functions.
    """
    return pd.DataFrame(
        {
            "sample_id": ["s1"] * 6,
            "drug_name": ["aspirin", "aspirin", "aspirin", "metformin", "metformin", "metformin"],
            "drugbank_id": ["DB00945"] * 3 + ["DB00331"] * 3,
            "drug_class": ["Salicylate"] * 3 + ["Biguanide"] * 3,
            "species": [
                "Bacteroides_fragilis",
                "Bacteroides_uniformis",
                "Bacteroides_ovatus",
                "Klebsiella_aerogenes",
                "Mediterraneibacter_gnavus",
                "Phocaeicola_dorei",
            ],
            "taxonomic_confidence": ["MEDIUM"] * 6,
            "microberx_score": [0.80, 0.60, 0.90, 0.70, 0.85, 0.50],
            "pathway_coverage_weight": [1.0] * 6,
            "interaction_confidence": [0.40, 0.30, 0.45, 0.35, 0.425, 0.25],
            "risk_tier": ["MEDIUM", "LOW", "MEDIUM", "LOW", "MEDIUM", "LOW"],
        }
    )


@pytest.fixture
def default_cfg() -> PKConfig:
    """PKConfig with new defaults (mif_scale_factor=0.5)."""
    return PKConfig()


@pytest.fixture
def minimal_metadata() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "drug_name": ["aspirin", "metformin"],
            "drugbank_id": ["DB00945", "DB00331"],
            "standard_dose_mg": [325.0, 500.0],
        }
    )


# ---------------------------------------------------------------------------
# 2a. MIF scale factor — the critical saturation fix
# ---------------------------------------------------------------------------
def _mif_scaled(mif: float, scale: float) -> float:
    """Replicate the formula: mif_scaled = clip(1 - exp(-MIF / scale), 0, 1)."""
    return float(np.clip(1.0 - np.exp(-mif / scale), 0.0, 1.0))


@pytest.mark.parametrize(
    "mif, scale, expected_mif_scaled",
    [
        # new scale=0.5: MIF=0.35 maps to ~0.503 — well within the dynamic range
        (0.35, 0.5,  pytest.approx(0.503, abs=0.01)),
        # old scale=20: MIF=0.35 saturates immediately at ~0.017 → clearance clipped
        (0.35, 20.0, pytest.approx(0.017, abs=0.01)),
        # zero MIF → zero scaled (no microbial signal)
        (0.0,  0.5,  pytest.approx(0.0,   abs=0.001)),
        # very large MIF → saturates at 1.0
        (5.0,  0.5,  pytest.approx(1.0,   abs=0.001)),
    ],
)
def test_mif_scaling(mif: float, scale: float, expected_mif_scaled: float) -> None:
    result = _mif_scaled(mif, scale)
    assert result == expected_mif_scaled, (
        f"mif_scaled({mif}, {scale}) = {result:.5f}, expected {expected_mif_scaled}"
    )


# ---------------------------------------------------------------------------
# 2b. compute_pk_impact() with known MIF — confirms scale fix end-to-end
# ---------------------------------------------------------------------------
def test_compute_pk_impact_near_neutral(
    sample_interactions_df: pd.DataFrame,
    minimal_metadata: pd.DataFrame,
) -> None:
    """
    With mif_scale_factor=0.5 and aspirin MIF ≈ 0.383:
    - mif_scaled ≈ 0.534  →  clearance ≈ 1.0 + (0.534-0.5)*0.6 ≈ 1.020
    - auc_mult   ≈ 1/1.020 ≈ 0.980  (NOT capped at 1.4)
    - dose_change_fraction ≈ 0.020  (near-zero, NOT −0.2857)
    """
    cfg = PKConfig(mif_scale_factor=0.5)
    result = compute_pk_impact(
        interactions=sample_interactions_df,
        metadata=minimal_metadata,
        cfg=cfg,
        sample_id="s1",
    )
    assert not result.empty, "Expected non-empty result for known inputs"

    aspirin_row = result[result["drug_name"] == "aspirin"].iloc[0]
    auc_mult = float(aspirin_row["predicted_auc_multiplier"])
    dose_change = float(aspirin_row["recommended_dose_change_fraction"])
    clearance_mult = float(aspirin_row["predicted_clearance_multiplier"])

    # AUC multiplier must NOT be at the 1.4 ceiling
    assert auc_mult < 1.35, (
        f"auc_multiplier={auc_mult:.4f} appears saturated at ceiling (expected < 1.35 with scale=0.5)"
    )
    # Dose change should be near-zero (within ±0.05)
    assert abs(dose_change) < 0.05, (
        f"dose_change_fraction={dose_change:.4f} expected near-zero with scale=0.5"
    )
    # Clearance should be near 1.0 (within ±0.05)
    assert abs(clearance_mult - 1.0) < 0.05, (
        f"clearance_multiplier={clearance_mult:.4f} expected near 1.0 with scale=0.5"
    )


def test_compute_pk_impact_legacy_scale_saturates(
    sample_interactions_df: pd.DataFrame,
    minimal_metadata: pd.DataFrame,
) -> None:
    """
    With mif_scale_factor=20 (legacy), MIF≈0.35 saturates → auc_mult at 1.4 ceiling.
    This is the regression guard to confirm the old bad behaviour is reproducible.
    """
    cfg = PKConfig(mif_scale_factor=20.0)
    result = compute_pk_impact(
        interactions=sample_interactions_df,
        metadata=minimal_metadata,
        cfg=cfg,
        sample_id="s1",
    )
    assert not result.empty
    aspirin_row = result[result["drug_name"] == "aspirin"].iloc[0]
    auc_mult = float(aspirin_row["predicted_auc_multiplier"])
    # With scale=20, should saturate near the clip bound
    assert auc_mult >= 1.39, (
        f"auc_multiplier={auc_mult:.4f} expected near ceiling 1.4 with scale=20"
    )


# ---------------------------------------------------------------------------
# 2c. Risk tier boundary conditions
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "ci_width, abs_change, expected_tier",
    [
        # HIGH: tight CI + large change
        (0.15, 0.25, "HIGH"),
        # MEDIUM: moderate CI + meaningful change
        (0.35, 0.12, "MEDIUM"),
        # LOW: large CI (high uncertainty)
        (0.50, 0.30, "LOW"),
        # LOW: small change regardless of CI
        (0.10, 0.05, "LOW"),
        # Boundary HIGH → MEDIUM: ci_width exactly 0.20 means HIGH is allowed
        (0.20, 0.20, "HIGH"),
        # Boundary MEDIUM → LOW: ci_width just above 0.40 → LOW
        (0.41, 0.15, "LOW"),
    ],
)
def test_risk_tier_boundaries(ci_width: float, abs_change: float, expected_tier: str) -> None:
    result = _tier_from_uncertainty(ci_width, abs_change)
    assert result == expected_tier, (
        f"_tier_from_uncertainty({ci_width}, {abs_change}) = {result!r}, expected {expected_tier!r}"
    )


# ---------------------------------------------------------------------------
# 2d. load_interactions() edge cases
# ---------------------------------------------------------------------------
def test_load_interactions_empty_tsv(tmp_path: Path) -> None:
    """Empty TSV (header only) should raise ValueError or return empty with an error."""
    empty_tsv = tmp_path / "empty.tsv"
    # Write only the header row — all required columns present but zero data rows.
    header = (
        "sample_id\tdrug_name\tdrugbank_id\tdrug_class\tspecies\t"
        "taxonomic_confidence\tmicroberx_score\tpathway_coverage_weight\t"
        "interaction_confidence\trisk_tier\n"
    )
    empty_tsv.write_text(header, encoding="utf-8")
    df = load_interactions(str(empty_tsv))
    assert df.empty, "Expected empty DataFrame for header-only TSV"


def test_load_interactions_missing_required_column(tmp_path: Path) -> None:
    """TSV missing 'interaction_confidence' must raise ValueError with column name in message."""
    bad_tsv = tmp_path / "bad.tsv"
    bad_tsv.write_text(
        "sample_id\tdrug_name\tdrugbank_id\tdrug_class\tspecies\t"
        "taxonomic_confidence\tmicroberx_score\tpathway_coverage_weight\trisk_tier\n"
        "s1\taspirin\tDB00945\tSalicylate\tB_frag\tMEDIUM\t0.8\t1.0\tMEDIUM\n",
        encoding="utf-8",
    )
    with pytest.raises((ValueError, KeyError)) as exc_info:
        load_interactions(str(bad_tsv))
    assert "interaction_confidence" in str(exc_info.value), (
        f"Expected 'interaction_confidence' in error message, got: {exc_info.value}"
    )


def test_load_interactions_nan_interaction_confidence(
    tmp_path: Path,
    sample_interactions_df: pd.DataFrame,
    minimal_metadata: pd.DataFrame,
) -> None:
    """
    NaN values in interaction_confidence should be dropped with a warning
    and NOT propagate silently through compute_pk_impact().
    """
    df_with_nan = sample_interactions_df.copy()
    df_with_nan.loc[0, "interaction_confidence"] = float("nan")

    cfg = PKConfig()
    result = compute_pk_impact(
        interactions=df_with_nan,
        metadata=minimal_metadata,
        cfg=cfg,
        sample_id="s1",
    )
    # Result must still be non-empty (remaining rows are valid)
    assert not result.empty, "Expected non-empty result after NaN rows are dropped"
    # MIF must be a finite number — not NaN
    assert result["microbiome_impact_factor"].notna().all(), (
        "microbiome_impact_factor contains NaN — NaN was not properly filtered"
    )


# ---------------------------------------------------------------------------
# 2e. SVG output smoke test (subprocess)
# ---------------------------------------------------------------------------
def test_svg_output_exists_and_valid(tmp_path: Path) -> None:
    """
    Run pk_impact.py as a subprocess on minimal test inputs and assert that
    the two SVG outputs are created and contain '<svg'.
    """
    # Minimal interactions TSV
    interactions_tsv = tmp_path / "test.interactions.tsv"
    interactions_tsv.write_text(
        "sample_id\tdrug_name\tdrugbank_id\tdrug_class\tspecies\t"
        "taxonomic_confidence\tmicroberx_score\tpathway_coverage_weight\t"
        "interaction_confidence\trisk_tier\n"
        "smoke\taspirin\tDB00945\tSalicylate\tB_fragilis\tMEDIUM\t0.8\t1.0\t0.40\tMEDIUM\n"
        "smoke\taspirin\tDB00945\tSalicylate\tB_ovatus\tMEDIUM\t0.9\t1.0\t0.45\tMEDIUM\n",
        encoding="utf-8",
    )

    # Empty metadata (will trigger fallback dose warning — that's OK)
    meta_csv = tmp_path / "empty_meta.csv"
    meta_csv.write_text("drug_name,drugbank_id\n", encoding="utf-8")

    pk_impact_script = Path(__file__).resolve().parent.parent.parent / "bin" / "pk_impact.py"

    result = subprocess.run(
        [
            sys.executable,
            str(pk_impact_script),
            "--sample-id", "smoke",
            "--interactions", str(interactions_tsv),
            "--drug-pk-metadata", str(meta_csv),
            "--output", str(tmp_path / "smoke.pk_impact.tsv"),
            "--summary-output", str(tmp_path / "smoke.pk_summary.tsv"),
            "--dose-plot-output", str(tmp_path / "smoke.dose_change.svg"),
            "--risk-plot-output", str(tmp_path / "smoke.risk_tier_counts.svg"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"pk_impact.py exited with {result.returncode}:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    )

    dose_svg = tmp_path / "smoke.dose_change.svg"
    risk_svg = tmp_path / "smoke.risk_tier_counts.svg"

    assert dose_svg.exists(), "dose_change.svg was not created"
    assert risk_svg.exists(), "risk_tier_counts.svg was not created"

    assert "<svg" in dose_svg.read_text(), "dose_change.svg does not contain '<svg'"
    assert "<svg" in risk_svg.read_text(), "risk_tier_counts.svg does not contain '<svg'"


def test_schema_version_header_in_output(tmp_path: Path, sample_interactions_df: pd.DataFrame) -> None:
    """
    The first line of *.pk_impact.tsv must be the schema version comment.
    """
    meta_csv = tmp_path / "empty_meta.csv"
    meta_csv.write_text("drug_name,drugbank_id\n", encoding="utf-8")

    pk_impact_script = Path(__file__).resolve().parent.parent.parent / "bin" / "pk_impact.py"

    interactions_tsv = tmp_path / "int.tsv"
    sample_interactions_df.to_csv(interactions_tsv, sep="\t", index=False)

    out_tsv = tmp_path / "out.pk_impact.tsv"
    subprocess.run(
        [
            sys.executable, str(pk_impact_script),
            "--sample-id", "s1",
            "--interactions", str(interactions_tsv),
            "--drug-pk-metadata", str(meta_csv),
            "--output", str(out_tsv),
            "--summary-output", str(tmp_path / "sum.tsv"),
            "--dose-plot-output", str(tmp_path / "dose.svg"),
            "--risk-plot-output", str(tmp_path / "risk.svg"),
        ],
        check=True,
        capture_output=True,
    )
    first_line = out_tsv.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("# rxbiome_pk_impact_schema_version="), (
        f"Expected schema version header, got: {first_line!r}"
    )
