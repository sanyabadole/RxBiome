/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW: PK_IMPACT_MODELING
    Deterministic exposure shift and dose recommendation per sample/drug.
    After PK_IMPACT, the four per-sample outputs are joined and fed into
    PK_REPORT_SAMPLE, which consolidates them into a single self-contained
    HTML QC report.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { PK_IMPACT        } from '../../modules/local/pk_impact/main'
include { PK_REPORT_SAMPLE } from '../../modules/local/pk_report_sample/main'

workflow PK_IMPACT_MODELING {
    take:
    ch_interactions    // channel: [ meta, interactions.tsv ]
    ch_drug_pk_metadata // channel: path(drug_pk_metadata.csv)

    main:
    ch_versions = Channel.empty()

    // ── Broadcast the shared metadata file to every sample ───────────────
    ch_pk_meta_keyed = ch_drug_pk_metadata.map { metadata_csv ->
        tuple("rxbiome_pk_metadata", metadata_csv)
    }
    ch_interactions_keyed = ch_interactions.map { meta, interactions ->
        tuple("rxbiome_pk_metadata", meta, interactions)
    }

    ch_pk_input = ch_interactions_keyed.join(ch_pk_meta_keyed, by: 0)
        .map { _key, meta, interactions, metadata_csv ->
            tuple(meta, interactions, metadata_csv)
        }

    // ── Module 4 core: compute PK impact per (sample, drug) ──────────────
    PK_IMPACT(ch_pk_input)
    ch_versions = ch_versions.mix(PK_IMPACT.out.versions)

    // ── Join the four per-sample outputs by meta so they arrive together ──
    // Result channel shape:
    //   [ meta, pk_impact.tsv, pk_summary.tsv, dose_change.svg, risk_tier_counts.svg ]
    ch_report_input = PK_IMPACT.out.pk_impact
        .join(PK_IMPACT.out.pk_summary)
        .join(PK_IMPACT.out.dose_plot)
        .join(PK_IMPACT.out.risk_plot)

    // ── Generate self-contained HTML QC report per sample ─────────────────
    PK_REPORT_SAMPLE(ch_report_input)
    ch_versions = ch_versions.mix(PK_REPORT_SAMPLE.out.versions)

    emit:
    qc_report  = PK_REPORT_SAMPLE.out.qc_report   // primary: HTML report per sample
    pk_impact  = PK_IMPACT.out.pk_impact           // secondary: raw TSV data
    pk_summary = PK_IMPACT.out.pk_summary          // secondary: per-sample summary
    dose_plot  = PK_IMPACT.out.dose_plot            // secondary: dose-change SVG
    risk_plot  = PK_IMPACT.out.risk_plot            // secondary: risk-tier SVG
    versions   = ch_versions
}
