process METAPHLAN4 {
    tag "$meta.id"
    label 'process_medium'

    // Image is on Docker Hub; this repo sets docker.registry=quay.io, so use an explicit docker.io/ URI (or docker:// for Singularity).
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'docker://biobakery/metaphlan:latest' :
        'docker.io/biobakery/metaphlan:latest' }"

    input:
    tuple val(meta), path(reads)
    path  db

    output:
    tuple val(meta), path("*.metaphlan4_profile.txt"),   emit: profile
    tuple val(meta), path("*.bowtie2.bz2"),              emit: bowtie2,   optional: true
    path  "versions.yml",                                emit: versions

    script:
    def prefix     = task.ext.prefix ?: "${meta.id}"
    def input_arg  = meta.single_end  ? "${reads[0]}" : "${reads[0]},${reads[1]}"
    // Index basename must match files in metaphlan4_db (e.g. mpa_vJan25_... not mpa_vJan21_...).
    def index      = params.metaphlan4_index?.toString()?.trim() ?: 'mpa_vJan25_CHOCOPhlAnSGB_202503'
    def db_arg     = db ? "--bowtie2db \$DB_REAL --index ${index}" : ""
    def db_setup   = db ? "DB_REAL=\$(readlink -f ${db})\n\n" : ''
    """
    ${db_setup}metaphlan \\
        ${input_arg} \\
        --input_type fastq \\
        --nproc ${task.cpus} \\
        ${db_arg} \\
        --output_file ${prefix}.metaphlan4_profile.txt \\
        --bowtie2out ${prefix}.bowtie2.bz2

    printf '"%s":\n    metaphlan: %s\n' \
        "${task.process}" \
        "\$(metaphlan --version 2>&1 | grep -oP '(?<=MetaPhlAn version )\\S+')" \
        > versions.yml
    """.stripIndent()

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}.metaphlan4_profile.txt
    touch ${prefix}.bowtie2.bz2

    printf '"%s":\n    metaphlan: 4.1.1\n' "${task.process}" > versions.yml
    """.stripIndent()
}