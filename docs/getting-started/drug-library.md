# Drug Library

The `--drugs` parameter points to a CSV file listing the drugs you want to score for microbiome interaction.

## Format

```csv
drug_name,drugbank_id,drug_class,smiles
metformin,DB00331,Biguanide,CN(C)C(=N)NC(=N)N
digoxin,DB00390,Cardiac glycoside,
warfarin,DB00682,Anticoagulant,
```

| Column | Required | Description |
|--------|----------|-------------|
| `drug_name` | Yes | Human-readable drug name (used in all outputs). |
| `drugbank_id` | Yes | DrugBank accession (e.g. `DB00331`). Used for SMILES lookup. |
| `drug_class` | Yes | Pharmacological class (e.g. `Statin`, `Anticoagulant`). |
| `smiles` | No | Canonical SMILES string. If provided, remote lookup is skipped for this row. |

## Pre-resolving SMILES

Network access inside pipeline containers is not always available. Pre-resolve SMILES **before** running the pipeline:

```bash
python bin/drug_smiles_lookup.py \
  --drug-library my_drugs.csv \
  --api-key "" \
  --output my_drugs.resolved.csv
```

The script tries these sources in order:

1. DrugBank REST API (requires `--api-key` if you have one)
2. PubChem REST API (free, no key required)
3. ChEMBL REST API (free, no key required)

Rows with `smiles` already filled are skipped.

!!! tip
    The resolved file uses **tab-separated** format (`.csv` extension preserved). The pipeline reads both comma- and tab-separated files automatically.

## Example Multi-Drug Cardiometabolic Panel

```csv
drug_name,drugbank_id,drug_class,smiles
digoxin,DB00390,Cardiac glycoside,
levodopa,DB01235,Antiparkinsonian,
irinotecan,DB00762,Antineoplastic,
sulfasalazine,DB00795,Anti-inflammatory,
metformin,DB00331,Biguanide,CN(C)C(=N)NC(=N)N
simvastatin,DB00641,Statin,
warfarin,DB00682,Anticoagulant,
tacrolimus,DB00864,Immunosuppressant,
```

These drugs were selected because they have well-documented microbiome interactions in the literature and span multiple metabolic pathways.

## Drug PK Metadata (Optional)

Supply drug-specific pharmacokinetic priors to improve dose adjustment accuracy:

```bash
nextflow run main.nf \
  --drugs my_drugs.resolved.csv \
  --drug_pk_metadata my_drug_pk.csv \
  ...
```

**PK metadata format** (`assets/schema_drug_pk_metadata.json`):

| Column | Description |
|--------|-------------|
| `drug_name` | Matches `drug_name` in drug library |
| `drugbank_id` | DrugBank accession |
| `standard_dose_mg` | Standard adult dose in mg |
| `target_auc` | Target AUC (optional) |
| `bioavailability_fraction` | Oral bioavailability 0–1 |
| `clearance_route` | `hepatic`, `renal`, or `mixed` |
| `therapeutic_index` | `narrow` or `wide` |

If `standard_dose_mg` is missing for a drug, the pipeline logs a warning and uses a fallback of 500 mg.
