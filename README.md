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

# 2. Run automated setup (checks tools, downloads databases + sample data)
bash quick_setup.sh

# 3. Run with test data (no databases needed)
nextflow run main.nf -profile test,docker --outdir results_test

# 4. Run with real data
nextflow run main.nf \
  -profile local,docker \
  --input samplesheet.csv \
  --drugs drug_library.csv \
  --kraken2_db databases/kraken2 \
  --metaphlan4_db databases/metaphlan \
  --metaphlan4_index mpa_vJan25_CHOCOPhlAnSGB_202503 \
  --outdir results/
```

### Download Sample Data Manually

If you prefer to download the example SRA samples yourself:

```bash
mkdir -p raw_data
# Download SRR413665 and SRR413666 from ENA (paired-end gut metagenomes)
wget -P raw_data https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR413/SRR413665/SRR413665_1.fastq.gz
wget -P raw_data https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR413/SRR413665/SRR413665_2.fastq.gz
wget -P raw_data https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR413/SRR413666/SRR413666_1.fastq.gz
wget -P raw_data https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR413/SRR413666/SRR413666_2.fastq.gz
```

### Download Databases Manually

```bash
# Kraken2 Standard 8 GB index
mkdir -p databases/kraken2
wget -P databases/kraken2 https://genome-idx.s3.amazonaws.com/kraken/k2_standard_08gb_20240112.tar.gz
tar -xzf databases/kraken2/k2_standard_08gb_20240112.tar.gz -C databases/kraken2
rm databases/kraken2/k2_standard_08gb_20240112.tar.gz

# MetaPhlAn 4 database
mkdir -p databases/metaphlan
metaphlan --install --index mpa_vJan25_CHOCOPhlAnSGB_202503 --bowtie2db databases/metaphlan

# KneadData human host database (required for host decontamination)
mkdir -p databases/kneaddata_human
kneaddata_database --download human_genome bowtie2 databases/kneaddata_human
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
