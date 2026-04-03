process KNEADDATA {
    tag "$meta.id"
    label 'process_high'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/kneaddata:0.12.0--pyhdfd78af_1' :
        'biocontainers/kneaddata:0.12.0--pyhdfd78af_1' }"

    input:
    tuple val(meta), path(reads)
    path  host_db

    output:
    tuple val(meta), path("*_kneaddata_paired_*.fastq.gz"), emit: reads
    tuple val(meta), path("*.log"),                         emit: log
    tuple val("${task.process}"), val('kneaddata'), eval('kneaddata --version 2>&1 | head -1'), emit: versions_kneaddata, topic: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args   = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    kneaddata \\
        --input1 ${reads[0]} \\
        --input2 ${reads[1]} \\
        --reference-db ${host_db} \\
        --output . \\
        --output-prefix ${prefix} \\
        --threads ${task.cpus} \\
        ${args}

    gzip *.fastq
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    echo '' | gzip > ${prefix}_kneaddata_paired_1.fastq.gz
    echo '' | gzip > ${prefix}_kneaddata_paired_2.fastq.gz
    touch "${prefix}.log"
    """
}