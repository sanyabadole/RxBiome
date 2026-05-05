/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW: PK_IMPACT_MODELING
    Deterministic exposure shift and dose recommendation per sample/drug.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { PK_IMPACT } from '../../modules/local/pk_impact/main'

workflow PK_IMPACT_MODELING {
    take:
    ch_interactions
    ch_drug_pk_metadata

    main:
    ch_versions = Channel.empty()

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

    PK_IMPACT(ch_pk_input)
    ch_versions = ch_versions.mix(PK_IMPACT.out.versions)

    emit:
    pk_impact = PK_IMPACT.out.pk_impact
    pk_summary = PK_IMPACT.out.pk_summary
    dose_plot = PK_IMPACT.out.dose_plot
    risk_plot = PK_IMPACT.out.risk_plot
    versions = ch_versions
}
