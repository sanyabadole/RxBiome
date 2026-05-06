# Samplesheet

The `--input` parameter must point to a comma-separated samplesheet file with the following columns.

## Step 1 — Place Your Raw Data

All FASTQ files should be placed inside a `raw_data/` folder in your pipeline directory before creating the samplesheet:

```
rxbiome/
├── raw_data/
│   ├── SRR413665_1.fastq.gz
│   ├── SRR413665_2.fastq.gz
│   ├── SRR413666_1.fastq.gz
│   └── SRR413666_2.fastq.gz
├── main.nf
├── nextflow.config
└── ...
```

```bash
mkdir -p raw_data
# copy or move your .fastq.gz files into raw_data/
cp /path/to/your/sequencing/*.fastq.gz raw_data/
```

!!! tip
    Always run `nextflow run` from the `rxbiome/` directory so that relative paths in the samplesheet resolve correctly.

## Step 2 — Create the Samplesheet

```csv
sample,fastq_1,fastq_2
SRR413665,raw_data/SRR413665_1.fastq.gz,raw_data/SRR413665_2.fastq.gz
SRR413666,raw_data/SRR413666_1.fastq.gz,raw_data/SRR413666_2.fastq.gz
```

| Column | Required | Description |
|--------|----------|-------------|
| `sample` | Yes | Unique sample identifier. No spaces. Used as output filename prefix. |
| `fastq_1` | Yes | Path to R1 FASTQ file (`.fastq.gz` or `.fq.gz`), relative to the pipeline launch directory or absolute. |
| `fastq_2` | No | Path to R2 FASTQ file. Omit or leave empty for single-end data. |

## Rules

- **Header row required** (`sample,fastq_1,fastq_2`).
- Prefer **relative paths** (e.g. `raw_data/sample_R1.fastq.gz`) so the samplesheet works on any machine. Absolute paths also work.
- Duplicate sample names across rows are allowed and will be **merged** before processing (useful for multi-lane data).
- Single-end data: leave `fastq_2` column empty (trailing comma).

## Example — Multi-lane Merge

```csv
sample,fastq_1,fastq_2
PATIENT_01,raw_data/P01_L001_R1.fastq.gz,raw_data/P01_L001_R2.fastq.gz
PATIENT_01,raw_data/P01_L002_R1.fastq.gz,raw_data/P01_L002_R2.fastq.gz
PATIENT_02,raw_data/P02_L001_R1.fastq.gz,raw_data/P02_L001_R2.fastq.gz
```

`PATIENT_01` will have both lanes concatenated before QC.

## Example — Single-end

```csv
sample,fastq_1,fastq_2
SRR000001,raw_data/SRR000001.fastq.gz,
```

## Validation

The pipeline validates the samplesheet automatically via `assets/schema_input.json`. Invalid rows cause an informative error before any compute begins.
