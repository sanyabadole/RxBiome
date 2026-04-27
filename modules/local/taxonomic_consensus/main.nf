process TAXONOMIC_CONSENSUS {
    tag "${meta.id}"
    label 'process_low'

    conda "conda-forge::python=3.11 conda-forge::pandas=2.2.1"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
    'https://depot.galaxyproject.org/singularity/pandas:2.2.1' :
    'quay.io/biocontainers/pandas:2.2.1' }"

    input:
    tuple val(meta), path(bracken_txt)
    tuple val(meta2), path(metaphlan_profile)

    output:
    tuple val(meta), path("*.consensus_taxonomy.tsv"), emit: consensus
    path "versions.yml", emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def prefix = task.ext.prefix ?: "${meta.id}"
    def bracken_min_fraction = params.bracken_min_fraction ?: 0.0001
    def metaphlan_min_abundance = params.metaphlan_min_abundance ?: 0.01
    """
    taxonomic_consensus.py \\
        --bracken ${bracken_txt} \\
        --metaphlan ${metaphlan_profile} \\
        --bracken-threshold ${bracken_min_fraction} \\
        --metaphlan-threshold ${metaphlan_min_abundance} \\
        --output ${prefix}.consensus_taxonomy.tsv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "\$(python --version | sed 's/Python //g')"
        pandas: "\$(python -c 'import pandas as pd; print(pd.__version__)')"
    END_VERSIONS
    """
}
