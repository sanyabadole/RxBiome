process HUMANN3 {
    tag "${meta.id}"
    label 'process_medium'

    conda "bioconda::humann=3.9"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
    'https://depot.galaxyproject.org/singularity/humann:3.9--py312hdfd78af_0' :
    'quay.io/biocontainers/humann:3.9--py312hdfd78af_0' }"

    input:
    tuple val(meta), path(reads)
    tuple val(meta2), path(metaphlan_profile)
    path nucleotide_db
    path protein_db

    output:
    tuple val(meta), path("*_genefamilies.tsv"), emit: genefamilies
    tuple val(meta), path("*_pathabundance.tsv"), emit: pathabundance
    tuple val(meta), path("*_pathcoverage.tsv"), emit: pathcoverage
    path "versions.yml", emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    if [ \$(echo "${reads}" | wc -w) -eq 2 ]; then
        cat ${reads} > ${prefix}_input.fastq.gz
    else
        ln -sf ${reads} ${prefix}_input.fastq.gz
    fi

    humann \\
      --input ${prefix}_input.fastq.gz \\
      --taxonomic-profile ${metaphlan_profile} \\
      --nucleotide-database ${nucleotide_db} \\
      --protein-database ${protein_db} \\
      --output . \\
      --output-basename ${prefix} \\
      --threads ${task.cpus} \\
      --metaphlan-options "--index ${params.metaphlan4_index}" \\
      ${args}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        humann: "\$(humann --version 2>&1 | sed 's/humann //')"
    END_VERSIONS
    """
}
