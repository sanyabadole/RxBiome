# Parameters Reference

All parameters are defined in `nextflow.config` and can be overridden on the command line with `--param_name value`.

## Input / Output

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--input` | `null` | Path to samplesheet CSV. **Required.** |
| `--drugs` | `null` | Path to drug library CSV/TSV. **Required.** |
| `--drug_pk_metadata` | `null` | Optional path to drug PK metadata CSV. |
| `--outdir` | `./results` | Directory for pipeline outputs. |
| `--email` | `null` | Completion notification email. |
| `--multiqc_title` | `null` | Custom MultiQC report title. |

## Sequencing

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--sequencing_type` | `paired` | `paired` or `single`. |

## Host Decontamination

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--skip_host_decontamination` | `false` | Set `true` to skip KneadData. |
| `--host_db` | `null` | Path to KneadData Bowtie2 database directory. |
| `--host_bowtie2_prefix` | `null` | Bowtie2 index prefix (e.g. `hg37dec_v0.1`). |

## Kraken2 / Bracken

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--kraken2_db` | `null` | Path to Kraken2 database directory. **Required.** |
| `--kraken2_confidence` | `0.0` | Confidence threshold for Kraken2 classification. |
| `--bracken_readlen` | `150` | Read length used for Bracken k-mer counting. |
| `--bracken_level` | `S` | Taxonomy level for Bracken (`S` = species). |

## MetaPhlAn 4

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--metaphlan4_db` | `null` | Path to MetaPhlAn 4 database directory. **Required.** |
| `--metaphlan4_index` | `null` | MetaPhlAn 4 index name. **Required.** |

## HUMAnN3 (Optional)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--humann3_nucleotide_db` | `null` | ChocoPhlAn nucleotide database path. |
| `--humann3_protein_db` | `null` | UniRef protein database path. |
| `--skip_humann3` | `false` | Force-skip HUMAnN3 even if DBs are provided. |

## MicrobeRX

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--microberx_min_confidence` | `0.1` | Minimum interaction confidence threshold. |
| `--drugbank_api_key` | `""` | DrugBank API key for SMILES resolution. |

## PK Impact Model Tuning

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--pk_mif_scale_factor` | `0.5` | MIF saturation divisor \(s\) in the Michaelis–Menten scaling. Increase for more conservative predictions. |
| `--pk_clearance_clip_min` | `-0.5` | Minimum allowed fractional clearance change. |
| `--pk_clearance_clip_max` | `0.8` | Maximum allowed fractional clearance change. |
| `--pk_auc_clip_min` | `-0.6` | Minimum allowed fractional AUC change. |
| `--pk_auc_clip_max` | `1.5` | Maximum allowed fractional AUC change. |
| `--pk_ci_base_uncertainty_scale` | `0.15` | Controls how much CI width grows with effect size. |
| `--pk_ci_min_offset` | `0.05` | Minimum CI half-width regardless of effect size. |

## Resource Limits

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--max_cpus` | `16` | Maximum CPUs per task. |
| `--max_memory` | `128.GB` | Maximum memory per task. |
| `--max_time` | `240.h` | Maximum wall time per task. |

## nf-core Boilerplate

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--help` | `false` | Print help message. |
| `--version` | `false` | Print pipeline version. |
| `--monochrome_logs` | `false` | Disable log coloring. |
| `--hook_url` | `null` | Slack/Teams webhook URL for notifications. |
| `--pipelines_testdata_base_path` | (nf-core S3) | Base URL for test data. |
| `--config_profile_name` | `null` | Profile name for `pipeline_info`. |
| `--config_profile_description` | `null` | Profile description. |
