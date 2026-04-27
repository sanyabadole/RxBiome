/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW: FUNCTIONAL_PROFILING
    HUMANN3 functional profiling using Module 1 MetaPhlAn output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { HUMANN3 } from '../../modules/local/humann3/main'

workflow FUNCTIONAL_PROFILING {

    take:
    ch_reads             // channel: [ val(meta), [ path(fastq_1), path(fastq_2) ] ]
    ch_metaphlan_profile // channel: [ val(meta), path(profile) ]

    main:

    def ch_genefamilies = Channel.empty()
    def ch_pathabundance = Channel.empty()
    def ch_pathcoverage = Channel.empty()
    def ch_versions = Channel.empty()

    if (!params.humann3_nucleotide_db || !params.humann3_protein_db) {
        log.warn '[rxbiome] HUMANnN3 DBs not set — skipping functional profiling. Set --humann3_nucleotide_db and --humann3_protein_db.'
    } else {
        ch_humann_input = ch_reads.join(ch_metaphlan_profile, by: 0)

        HUMANN3(
            ch_humann_input.map { meta, reads, profile -> [meta, reads] },
            ch_humann_input.map { meta, reads, profile -> [meta, profile] },
            Channel.value(file(params.humann3_nucleotide_db)),
            Channel.value(file(params.humann3_protein_db))
        )

        ch_genefamilies = HUMANN3.out.genefamilies
        ch_pathabundance = HUMANN3.out.pathabundance
        ch_pathcoverage = HUMANN3.out.pathcoverage
        ch_versions = HUMANN3.out.versions
    }

    emit:
    genefamilies  = ch_genefamilies
    pathabundance = ch_pathabundance
    pathcoverage  = ch_pathcoverage
    versions      = ch_versions
}
