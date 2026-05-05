/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT MODULES / SUBWORKFLOWS / FUNCTIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
include { MULTIQC                } from '../modules/nf-core/multiqc/main'
include { paramsSummaryMap       } from 'plugin/nf-schema'
include { paramsSummaryMultiqc   } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { softwareVersionsToYAML } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { methodsDescriptionText } from '../subworkflows/local/utils_nfcore_rxbiome_pipeline'
include { QC_PREPROCESSING       } from '../subworkflows/local/qc_preprocessing'
include { FUNCTIONAL_PROFILING   } from '../subworkflows/local/functional_profiling'
include { DRUG_MICROBIOME_INTERACTION } from '../subworkflows/local/drug_microbiome_interaction'
include { PK_IMPACT_MODELING } from '../subworkflows/local/pk_impact_modeling'
include { PK_REPORTING } from '../subworkflows/local/pk_reporting'

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    RUN MAIN WORKFLOW
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow RXBIOME {

    take:
    ch_samplesheet // channel: samplesheet read in from --input

    
    main:

    ch_versions = channel.empty()
    ch_multiqc_files = channel.empty()

    //
    // SUBWORKFLOW: Module 1 — QC & Preprocessing
    //
    QC_PREPROCESSING ( ch_samplesheet )
    ch_versions      = ch_versions.mix(QC_PREPROCESSING.out.versions)
    ch_multiqc_files = ch_multiqc_files.mix(QC_PREPROCESSING.out.multiqc_files)

    FUNCTIONAL_PROFILING(
        QC_PREPROCESSING.out.reads,
        QC_PREPROCESSING.out.metaphlan_profile
    )
    ch_versions = ch_versions.mix(FUNCTIONAL_PROFILING.out.versions)

    DRUG_MICROBIOME_INTERACTION(
        QC_PREPROCESSING.out.consensus_taxonomy,
        FUNCTIONAL_PROFILING.out.pathabundance,
        Channel.fromPath(params.drugs, checkIfExists: true)
    )
    ch_versions = ch_versions.mix(DRUG_MICROBIOME_INTERACTION.out.versions)

    ch_drug_pk_metadata = params.drug_pk_metadata ?
        Channel.fromPath(params.drug_pk_metadata, checkIfExists: true) :
        Channel.fromPath("${projectDir}/assets/empty_drug_pk_metadata.csv", checkIfExists: true)

    PK_IMPACT_MODELING(
        DRUG_MICROBIOME_INTERACTION.out.interactions,
        ch_drug_pk_metadata
    )
    ch_versions = ch_versions.mix(PK_IMPACT_MODELING.out.versions)

    PK_REPORTING(
        PK_IMPACT_MODELING.out.pk_impact
    )
    ch_versions = ch_versions.mix(PK_REPORTING.out.versions)

    //
    // Collate and save software versions
    //
    def topic_versions = Channel.topic("versions")
        .distinct()
        .branch { entry ->
            versions_file: entry instanceof Path
            versions_tuple: true
        }

    def topic_versions_string = topic_versions.versions_tuple
        .map { process, tool, version ->
            [ process[process.lastIndexOf(':')+1..-1], "  ${tool}: ${version}" ]
        }
        .groupTuple(by:0)
        .map { process, tool_versions ->
            tool_versions.unique().sort()
            "${process}:\n${tool_versions.join('\n')}"
        }

    softwareVersionsToYAML(ch_versions.mix(topic_versions.versions_file))
        .mix(topic_versions_string)
        .collectFile(
            storeDir: "${params.outdir}/pipeline_info",
            name: 'nf_core_'  +  'rxbiome_software_'  + 'mqc_'  + 'versions.yml',
            sort: true,
            newLine: true
        ).set { ch_collated_versions }


    //
    // MODULE: MultiQC
    //
    ch_multiqc_config        = channel.fromPath(
        "$projectDir/assets/multiqc_config.yml", checkIfExists: true)
    ch_multiqc_custom_config = params.multiqc_config ?
        channel.fromPath(params.multiqc_config, checkIfExists: true) :
        channel.empty()
    ch_multiqc_logo          = params.multiqc_logo ?
        channel.fromPath(params.multiqc_logo, checkIfExists: true) :
        channel.empty()

    summary_params      = paramsSummaryMap(
        workflow, parameters_schema: "nextflow_schema.json")
    ch_workflow_summary = channel.value(paramsSummaryMultiqc(summary_params))
    ch_multiqc_files = ch_multiqc_files.mix(
        ch_workflow_summary.collectFile(name: 'workflow_summary_mqc.yaml'))
    ch_multiqc_custom_methods_description = params.multiqc_methods_description ?
        file(params.multiqc_methods_description, checkIfExists: true) :
        file("$projectDir/assets/methods_description_template.yml", checkIfExists: true)
    ch_methods_description                = channel.value(
        methodsDescriptionText(ch_multiqc_custom_methods_description))

    ch_multiqc_files = ch_multiqc_files.mix(ch_collated_versions)
    ch_multiqc_files = ch_multiqc_files.mix(
        ch_methods_description.collectFile(
            name: 'methods_description_mqc.yaml',
            sort: true
        )
    )

    MULTIQC (
        ch_multiqc_files.collect(),
        ch_multiqc_config.toList(),
        ch_multiqc_custom_config.toList(),
        ch_multiqc_logo.toList(),
        [],
        []
    )

    emit:
    interactions  = DRUG_MICROBIOME_INTERACTION.out.interactions
    qc_report     = PK_IMPACT_MODELING.out.qc_report   // primary per-sample HTML report
    pk_impact     = PK_IMPACT_MODELING.out.pk_impact
    pk_summary    = PK_IMPACT_MODELING.out.pk_summary
    pk_dose_plot  = PK_IMPACT_MODELING.out.dose_plot
    pk_risk_plot  = PK_IMPACT_MODELING.out.risk_plot
    cohort_pk_impact = PK_REPORTING.out.cohort_pk_impact
    cohort_drug_summary = PK_REPORTING.out.cohort_drug_summary
    cohort_sample_summary = PK_REPORTING.out.cohort_sample_summary
    cohort_drug_plot = PK_REPORTING.out.cohort_drug_plot
    cohort_sample_plot = PK_REPORTING.out.cohort_sample_plot
    cohort_report_md = PK_REPORTING.out.cohort_report_md
    multiqc_report = MULTIQC.out.report.toList() // channel: /path/to/multiqc_report.html
    versions = ch_versions // channel: [ path(versions.yml) ]

}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
