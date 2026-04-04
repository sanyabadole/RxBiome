process KRAKEN2 {
    tag "$meta.id"
    label 'process_high'

    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/kraken2:2.17.1--pl5321h077b44d_0' :
        'biocontainers/kraken2:2.17.1--pl5321h077b44d_0' }"

    input:
    tuple val(meta), path(reads)
    path  db

    output:
    tuple val(meta), path("*.kraken2.report.txt"), emit: report
    tuple val(meta), path("*.kraken2.output.txt"), emit: output, optional: true
    path  "versions.yml",                          emit: versions

    script:
    def prefix      = task.ext.prefix ?: "${meta.id}"
    def paired_flag = meta.single_end  ? "" : "--paired"
    def db_arg      = db               ? "--db ${db}" : "--db \$KRAKEN2_DB"
    """
    kraken2 \\
        ${paired_flag} \\
        ${db_arg} \\
        --threads ${task.cpus} \\
        --report ${prefix}.kraken2.report.txt \\
        --output ${prefix}.kraken2.output.txt \\
        ${reads}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        kraken2: \$(kraken2 --version 2>&1 | head -1 | grep -oP '(?<=version )\\S+')
    END_VERSIONS
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}.kraken2.report.txt
    touch ${prefix}.kraken2.output.txt

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        kraken2: 2.17.1
    END_VERSIONS
    """
}