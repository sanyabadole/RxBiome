# Output Files

All outputs are written under `--outdir` (default `results/`). This page describes every file the pipeline produces.

## Directory Structure

```
results/
├── qc_preprocessing/
│   ├── {sample}.fastp.html
│   ├── {sample}.fastp.json
│   ├── {sample}.kraken2.txt
│   ├── {sample}.kraken2_report.txt
│   ├── {sample}_bracken_species.txt
│   ├── {sample}_profile.txt
│   └── {sample}.consensus_taxonomy.tsv
├── functional_profiling/          # only if HUMAnN3 enabled
│   ├── {sample}_genefamilies.tsv
│   ├── {sample}_pathabundance.tsv
│   └── {sample}_pathcoverage.tsv
├── drug_microbiome_interaction/
│   ├── {sample}.interactions.tsv
│   └── {sample}.dominant_species.tsv
├── pk_impact/
│   ├── {sample}.pk_impact.tsv
│   ├── {sample}.pk_summary.tsv
│   ├── {sample}.dose_change.svg
│   ├── {sample}.risk_tier_counts.svg
│   └── {sample}.qc_report.html       ← primary per-patient deliverable
├── pk_report/
│   ├── cohort_pk_impact.tsv
│   ├── cohort.drug_dose_change.svg
│   ├── cohort.risk_tier_summary.svg
│   ├── cohort.species_contribution.svg
│   └── cohort.pk_report.md
├── multiqc/
│   ├── multiqc_report.html
│   └── multiqc_data/
└── pipeline_info/
    ├── execution_report_*.html
    ├── execution_timeline_*.html
    ├── execution_trace_*.txt
    ├── pipeline_dag_*.html
    └── software_versions.yml
```

---

## Per-Sample Files

### `qc_preprocessing/{sample}.fastp.html`
Interactive QC report from fastp. Shows read counts before/after trimming, quality score distributions, GC content, and duplication rates.

### `qc_preprocessing/{sample}.consensus_taxonomy.tsv`
**Merged taxonomy table** — the primary output of Module 1. Columns:

| Column | Type | Description |
|--------|------|-------------|
| `species` | str | NCBI species name |
| `relative_abundance` | float | Normalised relative abundance (0–1) |
| `source` | str | `kraken2`, `metaphlan4`, or `consensus` |
| `confidence` | float | Agreement score between tools (0–1) |

### `drug_microbiome_interaction/{sample}.interactions.tsv`
Per-drug interaction scores output by MicrobeRX. See [Module 3](modules/module3-interaction.md) for schema.

### `pk_impact/{sample}.pk_impact.tsv`
Full per-drug PK impact predictions. Columns:

| Column | Type | Description |
|--------|------|-------------|
| `drug_name` | str | Drug identifier |
| `drug_class` | str | Pharmacological class |
| `mif_score` | float | Raw Microbiome Impact Factor |
| `mif_scaled` | float | Michaelis–Menten scaled MIF |
| `delta_clearance_frac` | float | Fractional clearance change |
| `delta_auc_frac` | float | Fractional AUC change |
| `dose_adj_fraction` | float | Recommended dose adjustment |
| `ci_lower` | float | 95% CI lower bound |
| `ci_upper` | float | 95% CI upper bound |
| `risk_tier` | str | `HIGH`, `MEDIUM`, or `LOW` |
| `dominant_species` | str | Top contributing species |

### `pk_impact/{sample}.qc_report.html`
**Self-contained HTML patient report**. Contains embedded SVG plots, Bootstrap-styled drug table, executive summary with risk tier counts, and clinical interpretation guide. Open in any web browser; can be printed to PDF.

---

## Cohort Files

### `pk_report/cohort.drug_dose_change.svg`
Three-panel heatmap:
- Drug × sample dose adjustment heatmap
- Risk tier annotation matrix
- Mean ± 1 SD dose change per drug (horizontal error bars)

### `pk_report/cohort.pk_report.md`
Markdown narrative report with:
- Cohort statistical summary table
- Top-5 dominant species table
- QC notes

---

## Pipeline Info

### `pipeline_info/software_versions.yml`
YAML listing every tool version used in the run. Suitable for Methods sections.

### `pipeline_info/execution_trace_*.txt`
Tab-separated resource usage trace: CPU %, memory, disk I/O, wall time for every task. Useful for optimising `--max_cpus` and `--max_memory`.

### `multiqc/multiqc_report.html`
Aggregated QC metrics across all samples from fastp (and optionally KneadData). Includes read count tables, quality histograms, and sample-level flags.
