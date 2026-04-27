/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW: DRUG_MICROBIOME_INTERACTION
    DrugBank lookup + MicrobeRX interaction prediction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { DRUG_SMILES_LOOKUP } from '../../modules/local/drug_smiles_lookup/main'
include { MICROBERX_PREDICT  } from '../../modules/local/microberx_predict/main'

workflow DRUG_MICROBIOME_INTERACTION {

    take:
    ch_consensus_taxonomy
    ch_pathabundance
    ch_drug_library_csv
    val_drugbank_api_key

    main:
    ch_versions = Channel.empty()

    DRUG_SMILES_LOOKUP(
        ch_drug_library_csv,
        val_drugbank_api_key
    )
    ch_versions = ch_versions.mix(DRUG_SMILES_LOOKUP.out.versions)

    ch_pathabundance_opt = ch_pathabundance.ifEmpty([])
    ch_pathabundance_fallback = ch_pathabundance_opt.ifEmpty(
        ch_consensus_taxonomy.map { meta, consensus_taxonomy ->
            [meta, file("$projectDir/assets/empty_pathabundance.tsv")]
        }
    )

    ch_consensus_pathabundance = ch_consensus_taxonomy
        .join(ch_pathabundance_fallback, by: 0)
        .map { meta, consensus_taxonomy, pathabundance ->
            [meta, consensus_taxonomy, pathabundance]
        }

    MICROBERX_PREDICT(
        ch_consensus_pathabundance.map { meta, consensus_taxonomy, pathabundance ->
            [meta, consensus_taxonomy]
        },
        DRUG_SMILES_LOOKUP.out.drugs_with_smiles,
        ch_consensus_pathabundance.map { meta, consensus_taxonomy, pathabundance ->
            [meta, pathabundance]
        }
    )
    ch_versions = ch_versions.mix(MICROBERX_PREDICT.out.versions)

    emit:
    interactions = MICROBERX_PREDICT.out.interactions
    versions = ch_versions
}
