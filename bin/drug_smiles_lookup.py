#!/usr/bin/env python3

import argparse
import csv
import json
import sys
import time
from urllib.parse import quote
from urllib.request import Request, urlopen
from pathlib import Path


OUTPUT_COLUMNS = ["drug_name", "drugbank_id", "drug_class", "smiles"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Lookup DrugBank compounds and append SMILES to a drug library."
    )
    parser.add_argument("--drug-library", required=True, help="Input drug library CSV path")
    parser.add_argument("--api-key", default="", help="DrugBank API key (optional)")
    parser.add_argument("--output", required=True, help="Output TSV with SMILES")
    return parser.parse_args()


def read_drug_library(path):
    rows = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"drug_name", "drugbank_id", "drug_class"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Drug library is missing required columns: {sorted(missing)}")
        for row in reader:
            rows.append(
                {
                    "drug_name": (row.get("drug_name") or "").strip(),
                    "drugbank_id": (row.get("drugbank_id") or "").strip(),
                    "drug_class": (row.get("drug_class") or "").strip(),
                }
            )
    return rows


def _http_get_json(url, headers=None, timeout=30):
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def fetch_smiles_from_drugbank(drugbank_id, api_key):
    if not drugbank_id:
        return ""

    # DrugBank release Swagger describes the endpoint family under /drug_names.
    # We keep this API failure-tolerant so upstream runs never hard fail.
    url = f"https://api.drugbank.com/v1/us/drugs/{drugbank_id}"
    headers = {"Authorization": api_key, "Accept": "application/json"}
    try:
        payload = _http_get_json(url, headers=headers, timeout=30)
    except Exception as exc:
        print(
            f"WARNING: DrugBank request failed for {drugbank_id}: {exc}",
            file=sys.stderr,
        )
        return ""

    # Handle common payload variants defensively.
    if isinstance(payload, dict):
        for key in ("smiles", "canonical_smiles", "calculated_properties"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if key == "calculated_properties" and isinstance(value, list):
                for prop in value:
                    if not isinstance(prop, dict):
                        continue
                    name = str(prop.get("kind") or prop.get("name") or "").lower()
                    if "smiles" in name:
                        prop_value = str(prop.get("value") or "").strip()
                        if prop_value:
                            return prop_value

    print(f"WARNING: No SMILES found for {drugbank_id}", file=sys.stderr)
    return ""


def fetch_smiles_from_pubchem(drug_name):
    if not drug_name:
        return ""
    encoded = quote(drug_name)
    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        f"{encoded}/property/CanonicalSMILES/JSON"
    )
    try:
        payload = _http_get_json(url, timeout=30)
    except Exception as exc:
        print(f"WARNING: PubChem lookup failed for {drug_name}: {exc}", file=sys.stderr)
        return ""

    props = (
        payload.get("PropertyTable", {}).get("Properties", [])
        if isinstance(payload, dict)
        else []
    )
    if props and isinstance(props[0], dict):
        return str(props[0].get("CanonicalSMILES") or "").strip()
    return ""


def fetch_smiles_from_chembl(drug_name):
    if not drug_name:
        return ""
    encoded = quote(drug_name)
    url = (
        "https://www.ebi.ac.uk/chembl/api/data/molecule/search"
        f"?q={encoded}&format=json"
    )
    try:
        payload = _http_get_json(url, timeout=30)
    except Exception as exc:
        print(f"WARNING: ChEMBL lookup failed for {drug_name}: {exc}", file=sys.stderr)
        return ""

    molecules = payload.get("molecules", []) if isinstance(payload, dict) else []
    for molecule in molecules:
        if not isinstance(molecule, dict):
            continue
        structures = molecule.get("molecule_structures") or {}
        smiles = str(structures.get("canonical_smiles") or "").strip()
        if smiles:
            return smiles
    return ""


def enrich_drugs_with_smiles(rows, api_key):
    use_drugbank = bool(api_key and str(api_key).strip())
    if not use_drugbank:
        print(
            "WARNING: --api-key not supplied; using PubChem/ChEMBL fallback for SMILES.",
            file=sys.stderr,
        )

    enriched = []
    for idx, row in enumerate(rows):
        smiles = ""
        if use_drugbank:
            smiles = fetch_smiles_from_drugbank(row["drugbank_id"], api_key)
            if idx < len(rows) - 1:
                time.sleep(1.0)
        if not smiles:
            smiles = fetch_smiles_from_pubchem(row["drug_name"])
        if not smiles:
            smiles = fetch_smiles_from_chembl(row["drug_name"])
        enriched.append({**row, "smiles": smiles})
    return enriched


def write_output_tsv(rows, out_path):
    with Path(out_path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in OUTPUT_COLUMNS})


def main():
    args = parse_args()
    rows = read_drug_library(args.drug_library)
    enriched = enrich_drugs_with_smiles(rows, args.api_key)
    write_output_tsv(enriched, args.output)


if __name__ == "__main__":
    main()
