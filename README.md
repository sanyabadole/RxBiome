# RxBiome

**Reproducible pharmacomicrobiomics — from gut metagenome to personalised dose adjustment**

[![Nextflow](https://img.shields.io/badge/nextflow%20DSL2-%E2%89%A523.04-23aa62.svg)](https://www.nextflow.io/)
[![nf-core](https://img.shields.io/badge/nf--core-standards-41b6a3.svg)](https://nf-co.re/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blueviolet)](https://sanyabadole.github.io/RxBiome/)

RxBiome is an nf-core–style Nextflow DSL2 pipeline that integrates shotgun metagenomics with pharmacokinetic (PK) modelling to predict how a patient's gut microbiome shifts drug exposure and recommend dose adjustments.

## Documentation

Full documentation with mathematical methods, usage guides, and output descriptions:

**[https://sanyabadole.github.io/RxBiome/](https://sanyabadole.github.io/RxBiome/)**

## Pipeline Overview

```
Raw FASTQ → QC & Preprocessing → Functional Profiling (optional)
         → Drug–Microbiome Interaction → PK Impact Modelling
         → Cohort Reporting → HTML patient reports + SVG plots
```

| Module | Tools |
|--------|-------|
| 1 — QC & Preprocessing | fastp, KneadData, Kraken2, Bracken, MetaPhlAn 4 |
| 2 — Functional Profiling | HUMAnN3 (optional) |
| 3 — Drug–Microbiome Interaction | MicrobeRX, PubChem, ChEMBL |
| 4 — PK Impact Modelling | Custom Python PK model |
| 5 — Cohort Reporting | matplotlib, Jinja2, pandas |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/sanyabadole/RxBiome.git
cd RxBiome

# 2. Run with test data
nextflow run main.nf -profile test,docker --outdir results_test

# 3. Run with your data
nextflow run main.nf \
  -profile local,docker \
  --input samplesheet.csv \
  --drugs drug_library.csv \
  --kraken2_db databases/kraken2 \
  --metaphlan4_db databases/metaphlan \
  --metaphlan4_index mpa_vJan25_CHOCOPhlAnSGB_202503 \
  --outdir results/
```

## Requirements

- [Nextflow](https://nextflow.io) ≥ 23.04
- [Docker](https://docker.com) or [Conda](https://conda.io)
- ≥ 16 GB RAM
- ≥ 50 GB disk for databases

## Citation

> Badole S. *RxBiome: a reproducible pharmacomicrobiomics pipeline.* GitHub (2026).

## License

MIT License — see [LICENSE](LICENSE).
