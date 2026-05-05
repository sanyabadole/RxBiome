/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW: PK_REPORTING
    Module 5.1 cohort-level report table aggregation.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { PK_REPORT_AGGREGATE } from '../../modules/local/pk_report_aggregate/main'
include { PK_REPORT_PLOTS } from '../../modules/local/pk_report_plots/main'
include { PK_REPORT_RENDER } from '../../modules/local/pk_report_render/main'

workflow PK_REPORTING {
    take:
    ch_pk_impact

    main:
    ch_versions = Channel.empty()

    ch_pk_impact_files = ch_pk_impact.map { meta, pk_impact_file -> pk_impact_file }.collect()

    PK_REPORT_AGGREGATE(ch_pk_impact_files)
    ch_versions = ch_versions.mix(PK_REPORT_AGGREGATE.out.versions)
    PK_REPORT_PLOTS(
        PK_REPORT_AGGREGATE.out.cohort_pk_impact,
        PK_REPORT_AGGREGATE.out.cohort_drug_summary,
        PK_REPORT_AGGREGATE.out.cohort_sample_summary
    )
    ch_versions = ch_versions.mix(PK_REPORT_PLOTS.out.versions)
    PK_REPORT_RENDER(
        PK_REPORT_AGGREGATE.out.cohort_pk_impact,
        PK_REPORT_AGGREGATE.out.cohort_drug_summary,
        PK_REPORT_AGGREGATE.out.cohort_sample_summary,
        PK_REPORT_PLOTS.out.drug_plot,
        PK_REPORT_PLOTS.out.sample_plot
    )
    ch_versions = ch_versions.mix(PK_REPORT_RENDER.out.versions)

    emit:
    cohort_pk_impact = PK_REPORT_AGGREGATE.out.cohort_pk_impact
    cohort_drug_summary = PK_REPORT_AGGREGATE.out.cohort_drug_summary
    cohort_sample_summary = PK_REPORT_AGGREGATE.out.cohort_sample_summary
    cohort_drug_plot = PK_REPORT_PLOTS.out.drug_plot
    cohort_sample_plot = PK_REPORT_PLOTS.out.sample_plot
    cohort_report_md = PK_REPORT_RENDER.out.report_md
    versions = ch_versions
}
