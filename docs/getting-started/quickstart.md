# Quick Start

This page walks through a real end-to-end run with two paired-end gut metagenome samples (SRR413665, SRR413666) and a 12-drug cardiometabolic panel.

## Step 1 — Place Your Raw Data and Create a Samplesheet

Copy your FASTQ files into a `raw_data/` folder inside the pipeline directory, then create the samplesheet using relative paths:

```bash
mkdir -p raw_data
cp /path/to/your/sequencing/SRR413665*.fastq.gz raw_data/
cp /path/to/your/sequencing/SRR413666*.fastq.gz raw_data/

cat > samplesheet.csv << 'EOF'
sample,fastq_1,fastq_2
SRR413665,raw_data/SRR413665_1.fastq.gz,raw_data/SRR413665_2.fastq.gz
SRR413666,raw_data/SRR413666_1.fastq.gz,raw_data/SRR413666_2.fastq.gz
EOF
```

!!! tip
    Always run `nextflow run` from the `rxbiome/` directory so that `raw_data/` relative paths resolve correctly on any machine.

## Step 2 — Create a Drug Library

```bash
cat > drugs.csv << 'EOF'
drug_name,drugbank_id,drug_class,smiles
metformin,DB00331,Biguanide,CN(C)C(=N)NC(=N)N
digoxin,DB00390,Cardiac glycoside,
warfarin,DB00682,Anticoagulant,
simvastatin,DB00641,Statin,
tacrolimus,DB00864,Immunosuppressant,
irinotecan,DB00762,Antineoplastic,
EOF

# Pre-resolve SMILES
python bin/drug_smiles_lookup.py \
  --drug-library drugs.csv \
  --api-key "" \
  --output drugs.resolved.csv
```

## Step 3 — Run (Skip Host Decontamination)

```bash
nextflow run main.nf \
  -profile local,docker \
  --input samplesheet.csv \
  --drugs drugs.resolved.csv \
  --kraken2_db databases/kraken2 \
  --metaphlan4_db databases/metaphlan \
  --metaphlan4_index mpa_vJan25_CHOCOPhlAnSGB_202503 \
  --skip_host_decontamination true \
  --outdir results/ \
  --max_cpus 4 \
  --max_memory 10.GB
```

## Step 3 (Alternative) — Run WITH Host Decontamination

```bash
nextflow run main.nf \
  -profile local,docker \
  --input samplesheet.csv \
  --drugs drugs.resolved.csv \
  --kraken2_db databases/kraken2 \
  --metaphlan4_db databases/metaphlan \
  --metaphlan4_index mpa_vJan25_CHOCOPhlAnSGB_202503 \
  --host_db databases/kneaddata_human \
  --host_bowtie2_prefix hg37dec_v0.1 \
  --outdir results/ \
  --max_cpus 4 \
  --max_memory 10.GB
```

## Step 4 — Monitor Progress

```bash
# Tail log for submitted/completed events
tail -f .nextflow.log | grep -E "Submitted|completed|ERROR"
```

```bash
# Summary table of tasks
nextflow log last -f 'process,status,duration,realtime,peak_rss,workdir'
```

## Step 5 — View Results

| Path | Contents |
|------|---------|
| `results/pk_impact/*.qc_report.html` | Per-patient HTML report |
| `results/pk_report/cohort.pk_report.md` | Cohort-level Markdown summary |
| `results/pk_report/cohort.drug_dose_change.svg` | Dose change heatmap |
| `results/multiqc/multiqc_report.html` | QC metrics dashboard |

Open the patient report in any browser:

```bash
open results/pk_impact/SRR413665.qc_report.html
```

## Resuming After a Failure

```bash
nextflow run main.nf [same arguments] -resume
```

Nextflow caches completed tasks in `work/`. `-resume` skips everything that succeeded and re-runs only from the point of failure.

## Resource Tips

| Stage | Typical time | Peak RAM |
|-------|-------------|----------|
| fastp | 2–5 min / sample | < 2 GB |
| KneadData | 20–90 min / sample | 4–8 GB |
| Kraken2 | 5–15 min / sample | 8 GB |
| MetaPhlAn | 15–30 min / sample | 4 GB |
| PK Impact (all modules) | < 2 min total | < 1 GB |

!!! tip
    Use `-profile local,docker` (comma, no spaces) to get local resource limits applied alongside Docker containers.
