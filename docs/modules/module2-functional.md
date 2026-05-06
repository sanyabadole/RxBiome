# Module 2 — Functional Profiling

<span class="step-badge">M2</span> **Subworkflow:** `subworkflows/local/functional_profiling.nf`

## Overview

Module 2 is **optional**. It runs HUMAnN3 to quantify microbial metabolic pathway abundances, giving a functional context to the species composition from Module 1. If the HUMAnN3 database paths are not provided, this module is silently skipped.

## Enabling Module 2

```bash
nextflow run main.nf \
  --humann3_nucleotide_db databases/humann3/chocophlan \
  --humann3_protein_db databases/humann3/uniref \
  ...
```

!!! info
    The pipeline checks for both database parameters at startup. If either is null, it emits a warning and proceeds without functional profiling. Module 3 receives an empty functional channel which is gracefully handled.

## HUMANN3 Process

| Item | Detail |
|------|--------|
| Tool | [HUMAnN3](https://huttenhower.sph.harvard.edu/humann/) v3.9 |
| Container | `quay.io/biocontainers/humann:3.9--pyh7cba7a3_0` |
| Label | `process_high_memory` |
| Nucleotide DB | ChocoPhlAn (passed via `--humann3_nucleotide_db`) |
| Protein DB | UniRef90 Diamond (passed via `--humann3_protein_db`) |

HUMAnN3 takes the MetaPhlAn 4 profile and the trimmed (or decontaminated) FASTQ as inputs and quantifies:

- **Gene families** (UniRef90-level)
- **Metabolic pathway coverage and abundance** (MetaCyc-level)

This is relevant for drugs that are metabolised by bacterial enzymes (e.g. irinotecan → SN-38 by bacterial β-glucuronidases, digoxin reduction by *Eggerthella lenta*).

## Output Files

| File | Description |
|------|-------------|
| `functional_profiling/{sample}_genefamilies.tsv` | Gene family RPKs |
| `functional_profiling/{sample}_pathabundance.tsv` | Pathway abundance (stratified) |
| `functional_profiling/{sample}_pathcoverage.tsv` | Pathway coverage |

## Relevance to Downstream Modules

The pathway abundance table is passed to Module 3 as supplementary context. In the current pipeline version this enhances the `interaction_confidence` scoring for drugs where specific bacterial enzyme pathways are known to be relevant (e.g. beta-glucuronidase activity for irinotecan).
