# Samplesheet

The `--input` parameter must point to a comma-separated samplesheet file with the following columns.

## Format

```csv
sample,fastq_1,fastq_2
SRR413665,/data/SRR413665_1.fastq.gz,/data/SRR413665_2.fastq.gz
SRR413666,/data/SRR413666_1.fastq.gz,/data/SRR413666_2.fastq.gz
```

| Column | Required | Description |
|--------|----------|-------------|
| `sample` | Yes | Unique sample identifier. No spaces. Used as output filename prefix. |
| `fastq_1` | Yes | Absolute path to R1 FASTQ file (`.fastq.gz` or `.fq.gz`). |
| `fastq_2` | No | Absolute path to R2 FASTQ file. Omit for single-end data. |

## Rules

- **Header row required** (`sample,fastq_1,fastq_2`).
- File paths must be **absolute** or relative to the pipeline launch directory.
- Duplicate sample names across rows are allowed and will be **merged** before processing (useful for multi-lane data).
- Single-end data: leave `fastq_2` column empty (trailing comma).

## Example — Multi-lane Merge

```csv
sample,fastq_1,fastq_2
PATIENT_01,/data/P01_L001_R1.fastq.gz,/data/P01_L001_R2.fastq.gz
PATIENT_01,/data/P01_L002_R1.fastq.gz,/data/P01_L002_R2.fastq.gz
PATIENT_02,/data/P02_L001_R1.fastq.gz,/data/P02_L001_R2.fastq.gz
```

`PATIENT_01` will have both lanes concatenated before QC.

## Example — Single-end

```csv
sample,fastq_1,fastq_2
SRR000001,/data/SRR000001.fastq.gz,
```

## Validation

The pipeline validates the samplesheet automatically via `assets/schema_input.json`. Invalid rows cause an informative error before any compute begins.
