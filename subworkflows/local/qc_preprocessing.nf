/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW: QC_PREPROCESSING
    fastp (trim) → KneadData (host decontamination) → MultiQC (report)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { FASTP     } from '../../modules/nf-core/fastp/main'
include { KNEADDATA } from '../../modules/local/kneaddata/main'
include { KRAKEN2_KRAKEN2 as KRAKEN2 } from '../../modules/nf-core/kraken2/kraken2/main'
include { BRACKEN_BRACKEN } from '../../modules/nf-core/bracken/bracken/main'
include { METAPHLAN4 } from '../../modules/local/metaphlan4/main'

workflow QC_PREPROCESSING {

    take:
    ch_reads    // channel: [ val(meta), [ path(fastq_1), path(fastq_2) ] ]

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
    // FASTP publishes version tuples to the versions topic only; omit them from ch_versions because
    // softwareVersionsToYAML expects YAML file paths (same pattern as other nf-core pipelines).
    ch_multiqc_files = ch_multiqc_files.mix(FASTP.out.json.map { meta, f -> f })
    ch_multiqc_files = ch_multiqc_files.mix(FASTP.out.html.map { meta, f -> f })

    //
    // MODULE: KNEADDATA — host decontamination
    // Runs whenever host removal is enabled (default). Requires --host_db.
    // Use --skip_host_decontamination for CI/stub runs without a host index (e.g. -profile test).
    //
    def ch_clean_reads
    if (params.skip_host_decontamination) {
        log.warn '[rxbiome] skip_host_decontamination=true — skipping KNEADDATA; using FASTP-trimmed reads downstream.'
        ch_clean_reads = FASTP.out.reads
    } else if (!params.host_db) {
        error("[rxbiome] KneadData requires --host_db (Bowtie2 host reference). " +
            "Download/build a KneadData-compatible host DB, or re-run with --skip_host_decontamination true " +
            "(not recommended for real WGS host removal).")
    } else {
        KNEADDATA (
            FASTP.out.reads,
            channel.value(file(params.host_db))
        )
        ch_clean_reads = KNEADDATA.out.reads
        ch_multiqc_files = ch_multiqc_files.mix(KNEADDATA.out.log.map { meta, f -> f })
    }

    //
    // TAXONOMIC PROFILING
    //
    KRAKEN2(
        ch_clean_reads,
        params.kraken2_db ? file(params.kraken2_db) : [],
        false, // save_output_fastqs
        false  // save_reads_assignment
    )
    ch_multiqc_files = ch_multiqc_files.mix(KRAKEN2.out.report.map { meta, f -> f })

    // Skip Bracken for empty reports or reports with no classified reads (taxid != 0 and reads > 0).
    ch_kraken2_report_for_bracken = KRAKEN2.out.report.filter { meta, report ->
        if (report.size() == 0) {
            return false
        }
        report.text.readLines().any { line ->
            def cols = line.trim().split(/\t+/)
            if (cols.size() < 5) {
                return false
            }
            try {
                return cols[4] != '0' && cols[1].toLong() > 0L
            } catch (Exception e) {
                return false
            }
        }
    }

    ch_kraken2_db_for_bracken = params.kraken2_db ? Channel.value(file(params.kraken2_db)) : Channel.empty()

    BRACKEN_BRACKEN(
        ch_kraken2_report_for_bracken,
        ch_kraken2_db_for_bracken
    )
    ch_multiqc_files = ch_multiqc_files.mix(BRACKEN_BRACKEN.out.txt.map { meta, f -> f })

    METAPHLAN4(
        ch_clean_reads,
        params.metaphlan4_db ? file(params.metaphlan4_db) : []
    )
    ch_versions = ch_versions.mix(METAPHLAN4.out.versions)

    emit:
    reads             = ch_clean_reads
    metaphlan_profile = METAPHLAN4.out.profile  
    kraken2_report    = KRAKEN2.out.report
    bracken_reports   = BRACKEN_BRACKEN.out.reports
    bracken_txt       = BRACKEN_BRACKEN.out.txt
    multiqc_files     = ch_multiqc_files
    versions          = ch_versions
}