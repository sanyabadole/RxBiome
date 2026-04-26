#!/usr/bin/env python3

import argparse
from pathlib import Path

import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create species-level taxonomic consensus from Bracken and MetaPhlAn4 outputs."
    )
    parser.add_argument("--bracken", required=True, help="Path to Bracken TSV output")
    parser.add_argument("--metaphlan", required=True, help="Path to MetaPhlAn4 profile output")
    parser.add_argument(
        "--bracken-threshold",
        type=float,
        default=0.0001,
        help="Minimum Bracken fraction_total_reads to pass (default: 0.0001)",
    )
    parser.add_argument(
        "--metaphlan-threshold",
        type=float,
        default=0.01,
        help="Minimum MetaPhlAn4 relative abundance to pass (default: 0.01)",
    )
    parser.add_argument("--output", required=True, help="Output consensus TSV path")
    return parser.parse_args()


def _empty_bracken_df():
    return pd.DataFrame(columns=["species", "bracken_fraction", "new_est_reads", "bracken_pass"])


def _empty_metaphlan_df():
    return pd.DataFrame(columns=["species", "metaphlan_abundance", "metaphlan_pass"])


def parse_bracken(path: str, threshold: float) -> pd.DataFrame:
    bracken_file = Path(path)
    if not bracken_file.exists() or bracken_file.stat().st_size == 0:
        return _empty_bracken_df()

    df = pd.read_csv(bracken_file, sep="\t")
    if df.empty:
        return _empty_bracken_df()

    required_cols = {"name", "taxonomy_lvl", "new_est_reads", "fraction_total_reads"}
    missing_cols = required_cols.difference(df.columns)
    if missing_cols:
        raise ValueError(f"Bracken file missing required columns: {sorted(missing_cols)}")

    species_df = df[df["taxonomy_lvl"] == "S"].copy()
    if species_df.empty:
        return _empty_bracken_df()

    species_df["species"] = species_df["name"].astype(str).str.strip()
    species_df["bracken_fraction"] = pd.to_numeric(
        species_df["fraction_total_reads"], errors="coerce"
    ).fillna(0.0)
    species_df["new_est_reads"] = pd.to_numeric(
        species_df["new_est_reads"], errors="coerce"
    ).fillna(0.0)
    species_df["bracken_pass"] = species_df["bracken_fraction"] >= threshold

    return species_df[["species", "bracken_fraction", "new_est_reads", "bracken_pass"]]


def parse_metaphlan(path: str, threshold: float) -> pd.DataFrame:
    metaphlan_file = Path(path)
    if not metaphlan_file.exists() or metaphlan_file.stat().st_size == 0:
        return _empty_metaphlan_df()

    rows = []
    with metaphlan_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split("\t")
            if len(parts) < 2:
                continue
            clade = parts[0]
            abundance = parts[1]
            if "|s__" not in clade or "|t__" in clade:
                continue
            species_token = clade.split("|s__", 1)[1].split("|", 1)[0].strip()
            if not species_token:
                continue
            species_name = species_token.replace("_", " ")
            rows.append((species_name, abundance))

    if not rows:
        return _empty_metaphlan_df()

    metaphlan_df = pd.DataFrame(rows, columns=["species", "metaphlan_abundance"])
    metaphlan_df["metaphlan_abundance"] = pd.to_numeric(
        metaphlan_df["metaphlan_abundance"], errors="coerce"
    ).fillna(0.0)
    metaphlan_df = metaphlan_df.groupby("species", as_index=False)["metaphlan_abundance"].max()
    metaphlan_df["metaphlan_pass"] = metaphlan_df["metaphlan_abundance"] >= threshold
    return metaphlan_df


def build_consensus(bracken_df: pd.DataFrame, metaphlan_df: pd.DataFrame) -> pd.DataFrame:
    consensus = pd.merge(bracken_df, metaphlan_df, on="species", how="outer")

    for col in ["bracken_fraction", "new_est_reads", "metaphlan_abundance"]:
        consensus[col] = pd.to_numeric(consensus[col], errors="coerce").fillna(0.0)
    for col in ["bracken_pass", "metaphlan_pass"]:
        consensus[col] = consensus[col].fillna(False).astype(bool)

    high_mask = consensus["bracken_pass"] & consensus["metaphlan_pass"]
    medium_mask = consensus["bracken_pass"] | consensus["metaphlan_pass"]
    consensus["confidence"] = "LOW"
    consensus.loc[medium_mask, "confidence"] = "MEDIUM"
    consensus.loc[high_mask, "confidence"] = "HIGH"

    consensus["final_abundance"] = consensus["bracken_fraction"] * 100.0
    consensus.loc[consensus["metaphlan_pass"], "final_abundance"] = consensus.loc[
        consensus["metaphlan_pass"], "metaphlan_abundance"
    ]

    confidence_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    consensus["confidence_rank"] = consensus["confidence"].map(confidence_order)
    consensus = consensus.sort_values(
        by=["confidence_rank", "final_abundance"], ascending=[True, False]
    ).drop(columns=["confidence_rank"])

    return consensus[
        [
            "species",
            "bracken_fraction",
            "new_est_reads",
            "metaphlan_abundance",
            "confidence",
            "final_abundance",
        ]
    ]


def print_summary(consensus_df: pd.DataFrame):
    counts = consensus_df["confidence"].value_counts()
    print("Consensus summary:")
    for tier in ["HIGH", "MEDIUM", "LOW"]:
        print(f"{tier}\t{int(counts.get(tier, 0))}")


def main():
    args = parse_args()
    bracken_df = parse_bracken(args.bracken, args.bracken_threshold)
    metaphlan_df = parse_metaphlan(args.metaphlan, args.metaphlan_threshold)
    consensus_df = build_consensus(bracken_df, metaphlan_df)
    consensus_df.to_csv(args.output, sep="\t", index=False)
    print_summary(consensus_df)


if __name__ == "__main__":
    main()
