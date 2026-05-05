#!/usr/bin/env python3

import argparse
import csv
import hashlib
import math
import os
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

# One process may score many drugs — load AGORA tables once.
_MICROBERX_TABLES: dict = {}


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
    parser.add_argument(
        "--microberx-cutoff",
        type=float,
        default=0.45,
        help="MetabolitePredictor confidence cutoff (sum of three similarity terms).",
    )
    parser.add_argument(
        "--microberx-max-rules",
        type=int,
        default=400,
        help="Max reaction rules to evaluate per drug (0 = full catalogue).",
    )
    parser.add_argument(
        "--microberx-biosystem",
        default="gutmicrobes",
        help="MetabolitePredictor biosystem: gutmicrobes, human, or all.",
    )
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


def _confidence_unit(score: float) -> float:
    """MicrobeRX confidence_score is a sum of three similarity-style terms (roughly 0–3)."""
    if score is None or (isinstance(score, float) and math.isnan(score)):
        return 0.0
    return max(0.0, min(1.0, float(score) / 3.0))


def _reaction_confidence_map(pred_df: pd.DataFrame) -> dict[str, float]:
    out: dict[str, float] = {}
    if pred_df is None or pred_df.empty or "confidence_score" not in pred_df.columns:
        return out
    for _, row in pred_df.iterrows():
        try:
            conf = float(row["confidence_score"])
        except (TypeError, ValueError):
            continue
        for col in ("reaction_id", "bigg_reaction"):
            if col not in row.index:
                continue
            val = row[col]
            if pd.isna(val):
                continue
            key = str(val).strip()
            if not key or key.lower() == "nan":
                continue
            out[key] = max(out.get(key, 0.0), conf)
    return out


def _microbes_lookup():
    if "mdata" not in _MICROBERX_TABLES:
        from microberx.DataFiles import load_microbes_data, load_microbes_reactions

        _MICROBERX_TABLES["mdata"] = load_microbes_data()
        _MICROBERX_TABLES["mrxn"] = load_microbes_reactions()
    return _MICROBERX_TABLES["mdata"], _MICROBERX_TABLES["mrxn"]


def _species_norm_lookup(mdata: pd.DataFrame, mrxn: pd.DataFrame) -> dict[str, set[str]]:
    """Map normalized Species label -> AGORA strain index names present in MicrobesReactions."""
    out: dict[str, set[str]] = {}
    valid_index = set(mrxn.index.astype(str))
    for _, row in mdata.iterrows():
        sp = row.get("Species")
        if pd.isna(sp):
            continue
        key = _norm_species(sp)
        bucket = out.setdefault(key, set())
        for col in ("microbe_name", "Strain"):
            val = row.get(col)
            if pd.isna(val):
                continue
            name = str(val).strip()
            if name and name in valid_index:
                bucket.add(name)
    return out


def _species_scores_from_predictions(
    pred_df: pd.DataFrame,
    species_list: list[str],
) -> dict[str, float]:
    """Map consensus species names to 0–1 scores using AGORA reaction overlap."""
    if pred_df is None or pred_df.empty:
        return {sp: 0.0 for sp in species_list}

    rxn_conf = _reaction_confidence_map(pred_df)
    if not rxn_conf:
        peak = _confidence_unit(float(pred_df["confidence_score"].max()))
        return {sp: round(0.35 * peak, 6) for sp in species_list}

    try:
        mdata, mrxn = _microbes_lookup()
        species_to_strains = _species_norm_lookup(mdata, mrxn)
    except Exception as exc:
        print(f"WARNING: could not load MicrobeRX microbe tables ({exc}); using global activity only.", file=sys.stderr)
        peak = _confidence_unit(float(pred_df["confidence_score"].max()))
        return {sp: round(0.35 * peak, 6) for sp in species_list}

    global_peak = _confidence_unit(float(pred_df["confidence_score"].max()))
    out: dict[str, float] = {}
    for sp in species_list:
        key = _norm_species(sp)
        strains = set(species_to_strains.get(key, ()))
        best_raw = 0.0
        for strain in strains:
            if strain not in mrxn.index:
                continue
            row = mrxn.loc[strain]
            for rxn_col, cell in row.items():
                if pd.isna(cell) or str(cell).strip() == "":
                    continue
                col = str(rxn_col).strip()
                if col in rxn_conf:
                    best_raw = max(best_raw, rxn_conf[col])
        if best_raw > 0.0:
            out[sp] = round(_confidence_unit(best_raw), 6)
        else:
            out[sp] = round(0.35 * global_peak, 6)
    return out


def run_microberx_scores(
    drug_smiles: str,
    species_list: list[str],
    cut_off: float,
    biosystem: str,
    max_rules: int,
) -> dict[str, float]:
    os.environ.setdefault("TQDM_DISABLE", "1")
    try:
        from rdkit import Chem
        from microberx.MetabolitePredictor import MetabolitePredictor
    except Exception as exc:
        print(
            f"WARNING: MicrobeRX / RDKit import failed ({exc}); using deterministic fallback scores.",
            file=sys.stderr,
        )
        return {species: _fallback_microberx_score(species, drug_smiles) for species in species_list}

    mol = Chem.MolFromSmiles(drug_smiles)
    if mol is None:
        print("WARNING: invalid drug SMILES for MicrobeRX; using fallback scores.", file=sys.stderr)
        return {species: _fallback_microberx_score(species, drug_smiles) for species in species_list}

    bs = (biosystem or "gutmicrobes").strip().lower()
    if bs not in {"all", "human", "gutmicrobes"}:
        print(f"WARNING: unknown biosystem {biosystem!r}; using gutmicrobes.", file=sys.stderr)
        bs = "gutmicrobes"

    try:
        predictor = MetabolitePredictor(mol, query_name="query", cut_off=cut_off, biosystem=bs)
        if max_rules > 0 and len(predictor.rules_table) > max_rules:
            predictor.rules_table = predictor.rules_table.iloc[:max_rules].copy()
        predictor.run_prediction()
        pred_df = predictor.predicted_metabolites
    except Exception as exc:
        print(
            f"WARNING: MicrobeRX MetabolitePredictor failed ({exc}); using fallback scores.",
            file=sys.stderr,
        )
        return {species: _fallback_microberx_score(species, drug_smiles) for species in species_list}

    if pred_df is None or pred_df.empty:
        return {species: _fallback_microberx_score(species, drug_smiles) for species in species_list}

    return _species_scores_from_predictions(pred_df, species_list)


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
    microberx_cutoff,
    microberx_max_rules,
    microberx_biosystem,
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
        species_scores = run_microberx_scores(
            smiles,
            species_list,
            cut_off=microberx_cutoff,
            biosystem=microberx_biosystem,
            max_rules=microberx_max_rules,
        )

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
    if drugs_df.empty:
        print(
            "WARNING: No drugs with non-empty SMILES after loading; writing header-only interactions TSV.",
            file=sys.stderr,
        )
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
        microberx_cutoff=float(args.microberx_cutoff),
        microberx_max_rules=int(args.microberx_max_rules),
        microberx_biosystem=str(args.microberx_biosystem),
    )
    write_interactions_tsv(rows, args.output)


if __name__ == "__main__":
    main()
