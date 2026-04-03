/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW: QC_PREPROCESSING
    fastp (trim) → KneadData (host decontamination) → MultiQC (report)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { FASTP     } from '../../modules/nf-core/fastp/main'
include { KNEADDATA } from '../../modules/local/kneaddata/main'

workflow QC_PREPROCESSING {

    take:
    ch_reads    // channel: [ val(meta), [ path(fastq_1), path(fastq_2) ] ]
    ch_host_db  // path: host reference database for KneadData

    main:

    ch_versions       = Channel.empty()
    ch_multiqc_files  = Channel.empty()

    //
    // MODULE: FASTP — trim adapters and low quality bases
    //
    FASTP (
        ch_reads.map { meta, reads -> [ meta, reads, [] ] },  
        false,  // discard_trimmed_pass
        false,  // save_trimmed_fail
        false   // save_merged
    )
    // FASTP emits version tuples to topic:versions; do not mix tuple versions into ch_versions,
    // because softwareVersionsToYAML expects YAML-file-style inputs!!! - ask aboout tthis error later, only fix found
    ch_multiqc_files = ch_multiqc_files.mix(FASTP.out.json.map { meta, f -> f })
    ch_multiqc_files = ch_multiqc_files.mix(FASTP.out.html.map { meta, f -> f })

    //
    // MODULE: KNEADDATA — remove host (human) reads 
    //
    KNEADDATA (
        FASTP.out.reads,  // takes trimmed reads directly from FASTP
        ch_host_db
    )
    // KNEADDATA also emits version tuples to topic:versions.
    ch_multiqc_files = ch_multiqc_files.mix(KNEADDATA.out.log.map { meta, f -> f })

    emit:
    clean_reads   = KNEADDATA.out.reads  // [ val(meta), [ clean_R1, clean_R2 ] ] → Module 2
    multiqc_files = ch_multiqc_files     // fastp json/html + kneaddata logs → MultiQC
    versions      = ch_versions          // tool versions → provenance tracking!!! imp for reproducibility <3
}