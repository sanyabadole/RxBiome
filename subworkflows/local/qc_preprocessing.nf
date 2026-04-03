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
        ch_reads,
        [],     // no adapter fasta — use auto-detection (--detect_adapter_for_pe)
        false,  // discard_trimmed_pass = false (keep passing reads)
        false,  // save_trimmed_fail = false
        false   // save_merged = false
    )
    ch_versions      = ch_versions.mix(FASTP.out.versions_fastp)
    ch_multiqc_files = ch_multiqc_files.mix(FASTP.out.json)
    ch_multiqc_files = ch_multiqc_files.mix(FASTP.out.html)

    //
    // MODULE: KNEADDATA — remove host (human) reads 
    //
    KNEADDATA (
        FASTP.out.reads,  // takes trimmed reads directly from FASTP
        ch_host_db
    )
    ch_versions      = ch_versions.mix(KNEADDATA.out.versions_kneaddata)
    ch_multiqc_files = ch_multiqc_files.mix(KNEADDATA.out.log)

    emit:
    clean_reads   = KNEADDATA.out.reads  // [ val(meta), [ clean_R1, clean_R2 ] ] → Module 2
    multiqc_files = ch_multiqc_files     // fastp json/html + kneaddata logs → MultiQC
    versions      = ch_versions          // tool versions → provenance tracking!!! imp for reproducibility <3
}