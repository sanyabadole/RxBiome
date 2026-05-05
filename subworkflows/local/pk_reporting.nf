/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW: PK_REPORTING
    Module 5.1 cohort-level report table aggregation.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { PK_REPORT_AGGREGATE } from '../../modules/local/pk_report_aggregate/main'

workflow PK_REPORTING {
    take:
    ch_pk_impact

    main:
    ch_versions = Channel.empty()

    ch_pk_impact_files = ch_pk_impact.map { meta, pk_impact_file -> pk_impact_file }.collect()

    PK_REPORT_AGGREGATE(ch_pk_impact_files)
    ch_versions = ch_versions.mix(PK_REPORT_AGGREGATE.out.versions)

    emit:
    cohort_pk_impact = PK_REPORT_AGGREGATE.out.cohort_pk_impact
    cohort_drug_summary = PK_REPORT_AGGREGATE.out.cohort_drug_summary
    cohort_sample_summary = PK_REPORT_AGGREGATE.out.cohort_sample_summary
    versions = ch_versions
}
