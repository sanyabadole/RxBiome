#!/usr/bin/env bash
set -euo pipefail

OUTDIR="tests/data/pk_impact_test_outputs"
rm -rf "${OUTDIR}"
mkdir -p "${OUTDIR}"

echo "=== MODULE 4.5 PK IMPACT MOCK COHORT TEST ==="

for SAMPLE in SAMPLE_A SAMPLE_B; do
  python bin/pk_impact.py \
    --sample-id "${SAMPLE}" \
    --interactions tests/data/mock_drug_interactions_cohort.tsv \
    --drug-pk-metadata tests/data/mock_drug_pk_metadata.csv \
    --target-exposure-multiplier 1.0 \
    --max-dose-adjustment-fraction 0.5 \
    --min-confidence-interval-width 0.1 \
    --output "${OUTDIR}/${SAMPLE}.pk_impact.tsv" \
    --summary-output "${OUTDIR}/${SAMPLE}.pk_summary.tsv" \
    --dose-plot-output "${OUTDIR}/${SAMPLE}.dose_change.svg" \
    --risk-plot-output "${OUTDIR}/${SAMPLE}.risk_tier_counts.svg"
done

python - <<'PY'
from pathlib import Path
import pandas as pd

outdir = Path("tests/data/pk_impact_test_outputs")
samples = ["SAMPLE_A", "SAMPLE_B"]

for sample in samples:
    pk = pd.read_csv(outdir / f"{sample}.pk_impact.tsv", sep="\t")
    summary = pd.read_csv(outdir / f"{sample}.pk_summary.tsv", sep="\t")
    dose_svg = (outdir / f"{sample}.dose_change.svg").read_text(encoding="utf-8")
    risk_svg = (outdir / f"{sample}.risk_tier_counts.svg").read_text(encoding="utf-8")

    assert len(pk) == 2, f"{sample}: expected 2 drug rows, got {len(pk)}"
    assert set(pk["drug_name"]) == {"metformin", "aspirin"}, f"{sample}: unexpected drug set"
    assert pk["dominant_species"].notna().all(), f"{sample}: dominant_species contains null"
    assert (pk["recommended_dose_mg"] > 0).all(), f"{sample}: non-positive recommended dose detected"
    assert (pk["confidence_high"] >= pk["confidence_low"]).all(), f"{sample}: invalid confidence interval ordering"
    assert summary.loc[0, "n_drugs"] == 2, f"{sample}: summary n_drugs mismatch"
    assert dose_svg.lstrip().startswith("<svg"), f"{sample}: dose plot is not svg"
    assert risk_svg.lstrip().startswith("<svg"), f"{sample}: risk plot is not svg"

print("ALL MODULE 4.5 ASSERTIONS PASSED ✓")
PY

echo "Outputs written to ${OUTDIR}"
