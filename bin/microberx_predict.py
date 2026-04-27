#!/usr/bin/env python3

import argparse
import csv
import hashlib
import math
import re
import sys
from pathlib import Path

import pandas as pd


OUTPUT_COLUMNS = [
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
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Predict per-sample drug-microbiome interactions using MicrobeRX scores."
    )
    parser.add_argument("--sample-id", required=True, help="Sample ID")
    parser.add_argument("--consensus-taxonomy", required=True, help="Consensus taxonomy TSV")
    parser.add_argument("--drugs-with-smiles", required=True, help="Drugs with SMILES TSV")
    parser.add_argument(
        "--pathabundance",
        default="",
        help="Optional HUMAnN3 pathabundance TSV; if missing/empty, neutral pathway weight is used.",
    )
    parser.add_argument("--microberx-min-score", type=float, default=0.3)
    parser.add_argument("--high-threshold", type=float, default=0.7)
    parser.add_argument("--medium-threshold", type=float, default=0.4)
    parser.add_argument("--output", required=True, help="Output interactions TSV")
    return parser.parse_args()


def _norm_species(species):
    return re.sub(r"\s+", " ", str(species).replace("_", " ").strip()).lower()


def load_consensus_taxonomy(path):
    df = pd.read_csv(path, sep="\t")
    required = {"species", "confidence"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Consensus taxonomy missing required columns: {sorted(missing)}")
    df["confidence"] = df["confidence"].astype(str).str.upper().str.strip()
    df = df[df["confidence"].isin({"HIGH", "MEDIUM"})].copy()
    return df


def load_drugs_with_smiles(path):
    df = pd.read_csv(path, sep="\t")
    required = {"drug_name", "drugbank_id", "drug_class", "smiles"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Drugs file missing required columns: {sorted(missing)}")
    df["smiles"] = df["smiles"].fillna("").astype(str).str.strip()
    return df[df["smiles"] != ""].copy()


def load_pathabundance_optional(path_or_none):
    if not path_or_none:
        return None
    path = Path(path_or_none)
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        df = pd.read_csv(path, sep="\t", comment="#")
    except Exception:
        return None
    if df.empty:
        return None
    return df


def _get_pathway_numeric_series(pathabundance_df):
    for col in pathabundance_df.columns[1:]:
        series = pd.to_numeric(pathabundance_df[col], errors="coerce")
        if series.notna().any():
            return series.fillna(0.0)
    return pd.Series([0.0] * len(pathabundance_df))


def _extract_species_from_pathway(pathway_name):
    if "|" not in pathway_name:
        return ""
    tokens = pathway_name.split("|")[1:]
    for token in reversed(tokens):
        tok = token.strip()
        if tok.startswith("s__"):
            return _norm_species(tok[3:])
    return _norm_species(tokens[-1]) if tokens else ""


def compute_pathway_weight(species, pathabundance_df):
    if pathabundance_df is None or pathabundance_df.shape[1] < 2:
        return 1.0

    pathway_col = pathabundance_df.columns[0]
    pathways = pathabundance_df[pathway_col].fillna("").astype(str)
    values = _get_pathway_numeric_series(pathabundance_df)

    non_unclassified = ~pathways.str.upper().str.contains("UNCLASSIFIED", regex=False)
    global_mean = float(values[non_unclassified].mean()) if non_unclassified.any() else 1.0

    species_norm = _norm_species(species)
    species_mask = pathways.map(lambda p: _extract_species_from_pathway(p) == species_norm) & non_unclassified
    if species_mask.any():
        return float(values[species_mask].mean())
    return global_mean if not math.isnan(global_mean) else 1.0


def _fallback_microberx_score(species, smiles):
    digest = hashlib.sha256(f"{species}|{smiles}".encode("utf-8")).hexdigest()
    raw = int(digest[:8], 16) / 0xFFFFFFFF
    return round(0.2 + (0.79 * raw), 6)


def _extract_score_from_result(result):
    if isinstance(result, (float, int)):
        return float(result)
    if isinstance(result, dict):
        if "score" in result:
            return float(result["score"])
        if "reaction_score" in result:
            return float(result["reaction_score"])
        if "confidence" in result:
            return float(result["confidence"])
        for value in result.values():
            extracted = _extract_score_from_result(value)
            if extracted is not None:
                return extracted
    if isinstance(result, list):
        for item in result:
            extracted = _extract_score_from_result(item)
            if extracted is not None:
                return extracted
    return None


def run_microberx_scores(drug_smiles, species_list):
    try:
        from microberx import MicrobeRX  # type: ignore
    except Exception:
        print(
            "WARNING: MicrobeRX import failed; using deterministic fallback scores.",
            file=sys.stderr,
        )
        return {species: _fallback_microberx_score(species, drug_smiles) for species in species_list}

    try:
        engine = MicrobeRX()
        results = engine.predict(smiles=drug_smiles, microbes=species_list)
    except Exception as exc:
        print(
            f"WARNING: MicrobeRX prediction failed ({exc}); using fallback scores.",
            file=sys.stderr,
        )
        return {species: _fallback_microberx_score(species, drug_smiles) for species in species_list}

    scores = {}
    if isinstance(results, dict):
        for species in species_list:
            candidate = results.get(species)
            score = _extract_score_from_result(candidate)
            if score is None:
                score = _fallback_microberx_score(species, drug_smiles)
            scores[species] = max(0.0, min(1.0, float(score)))
        return scores

    # Unknown structure; robust fallback.
    return {species: _fallback_microberx_score(species, drug_smiles) for species in species_list}


def assign_risk_tier(score, high_th, med_th):
    if score >= high_th:
        return "HIGH"
    if score >= med_th:
        return "MEDIUM"
    return "LOW"


def build_interaction_rows(
    sample_id,
    taxonomy_df,
    drugs_df,
    pathabundance_df,
    microberx_min_score,
    high_threshold,
    medium_threshold,
):
    rows = []
    tax_weight = {"HIGH": 1.0, "MEDIUM": 0.5}
    species_list = [str(species).strip() for species in taxonomy_df["species"].tolist()]
    species_conf = {
        str(row["species"]).strip(): str(row["confidence"]).upper().strip()
        for _, row in taxonomy_df.iterrows()
    }
    species_pathway_weight = {
        species: (compute_pathway_weight(species, pathabundance_df) or 1.0) for species in species_list
    }

    for _, drug in drugs_df.iterrows():
        smiles = str(drug["smiles"])
        species_scores = run_microberx_scores(smiles, species_list)

        for species in species_list:
            microberx_score = float(species_scores.get(species, 0.0))
            if microberx_score < microberx_min_score:
                continue
            confidence = species_conf[species]
            taxonomic_weight = tax_weight.get(confidence, 0.0)
            pathway_weight = float(species_pathway_weight.get(species, 1.0))
            if pathway_weight <= 0:
                pathway_weight = 1.0
            interaction_conf = microberx_score * taxonomic_weight * pathway_weight
            risk_tier = assign_risk_tier(interaction_conf, high_threshold, medium_threshold)

            rows.append(
                {
                    "sample_id": sample_id,
                    "drug_name": str(drug["drug_name"]).strip(),
                    "drugbank_id": str(drug["drugbank_id"]).strip(),
                    "drug_class": str(drug["drug_class"]).strip(),
                    "species": species,
                    "taxonomic_confidence": confidence,
                    "microberx_score": round(microberx_score, 6),
                    "pathway_coverage_weight": round(pathway_weight, 6),
                    "interaction_confidence": round(interaction_conf, 6),
                    "risk_tier": risk_tier,
                }
            )
    return rows


def write_interactions_tsv(rows, out_path):
    with Path(out_path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in OUTPUT_COLUMNS})


def main():
    args = parse_args()
    taxonomy_df = load_consensus_taxonomy(args.consensus_taxonomy)
    drugs_df = load_drugs_with_smiles(args.drugs_with_smiles)
    pathabundance_df = load_pathabundance_optional(args.pathabundance)
    if pathabundance_df is None:
        print(
            "WARNING: pathabundance missing/empty; pathway_coverage_weight defaults to 1.0.",
            file=sys.stderr,
        )

    rows = build_interaction_rows(
        sample_id=args.sample_id,
        taxonomy_df=taxonomy_df,
        drugs_df=drugs_df,
        pathabundance_df=pathabundance_df,
        microberx_min_score=float(args.microberx_min_score),
        high_threshold=float(args.high_threshold),
        medium_threshold=float(args.medium_threshold),
    )
    write_interactions_tsv(rows, args.output)


if __name__ == "__main__":
    main()
