# Pipeline Modules

RxBiome is structured as five sequential modules, each implemented as an nf-core–style Nextflow subworkflow.

```mermaid
flowchart TD
    subgraph M1 ["Module 1 — QC & Preprocessing"]
        fastp --> kneaddata --> kraken2 --> bracken --> metaphlan --> consensus
    end
    subgraph M2 ["Module 2 — Functional Profiling (optional)"]
        humann3
    end
    subgraph M3 ["Module 3 — Drug–Microbiome Interaction"]
        smiles_lookup --> microberx
    end
    subgraph M4 ["Module 4 — PK Impact Modelling"]
        pk_impact --> pk_report_sample
    end
    subgraph M5 ["Module 5 — Cohort Reporting"]
        pk_aggregate --> pk_plots --> pk_render
    end

    M1 --> M2
    M1 --> M3
    M2 --> M3
    M3 --> M4
    M4 --> M5
```

| Module | Subworkflow file | Key processes |
|--------|----------------|---------------|
| [1 — QC & Preprocessing](module1-qc.md) | `qc_preprocessing.nf` | FASTP, KNEADDATA, KRAKEN2, BRACKEN, METAPHLAN4, TAXONOMIC_CONSENSUS |
| [2 — Functional Profiling](module2-functional.md) | `functional_profiling.nf` | HUMANN3 |
| [3 — Drug–Microbiome Interaction](module3-interaction.md) | `drug_microbiome_interaction.nf` | DRUG_SMILES_LOOKUP, MICROBERX_PREDICT |
| [4 — PK Impact Modelling](module4-pk-impact.md) | `pk_impact_modeling.nf` | PK_IMPACT, PK_REPORT_SAMPLE |
| [5 — Cohort Reporting](module5-reporting.md) | `pk_reporting.nf` | PK_REPORT_AGGREGATE, PK_REPORT_PLOTS, PK_REPORT_RENDER |
