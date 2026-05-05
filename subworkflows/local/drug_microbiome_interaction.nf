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

    main:
    ch_versions = Channel.empty()

    DRUG_SMILES_LOOKUP(
        ch_drug_library_csv
    )
    ch_versions = ch_versions.mix(DRUG_SMILES_LOOKUP.out.versions)

    // Avoid dual-consuming consensus channel: construct the final tuple in one pass when HUMAnN is skipped.
    ch_consensus_pathabundance = (
        !params.humann3_nucleotide_db || !params.humann3_protein_db
    ) ? ch_consensus_taxonomy.map { meta, consensus_taxonomy ->
            [meta, consensus_taxonomy, file("${projectDir}/assets/empty_pathabundance.tsv")]
        }
      : ch_consensus_taxonomy
            .join(ch_pathabundance, by: 0)
            .map { meta, consensus_taxonomy, pathabundance ->
                [meta, consensus_taxonomy, pathabundance]
            }

    // Broadcast the single drugs TSV to every sample (queue channel would be consumed after one task).
    ch_drugs_keyed = DRUG_SMILES_LOOKUP.out.drugs_with_smiles.map { drugs_tsv ->
        tuple('rxbiome_drugs', drugs_tsv)
    }
    ch_samples_keyed = ch_consensus_pathabundance.map { meta, consensus_taxonomy, pathabundance ->
        tuple('rxbiome_drugs', meta, consensus_taxonomy, pathabundance)
    }
    ch_microberx_in = ch_samples_keyed.join(ch_drugs_keyed, by: 0)
        .map { _k, meta, consensus_taxonomy, pathabundance, drugs_tsv ->
            tuple(meta, consensus_taxonomy, drugs_tsv, pathabundance)
        }

    MICROBERX_PREDICT(ch_microberx_in)
    ch_versions = ch_versions.mix(MICROBERX_PREDICT.out.versions)

    emit:
    interactions = MICROBERX_PREDICT.out.interactions
    versions = ch_versions
}
