process MICROBERX_PREDICT {
    tag "${meta.id}"
    label 'process_medium'

    conda "conda-forge::python=3.11 conda-forge::pandas=2.2.1 conda-forge::numpy requests pip"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
    'docker://docker.io/sanyabadole/rxbiome-microberx:1.0' :
    'docker.io/sanyabadole/rxbiome-microberx:1.0' }"

    input:
    tuple val(meta), path(consensus_taxonomy)
    path drugs_with_smiles
    tuple val(meta2), path(pathabundance)

    output:
    tuple val(meta), path("*.drug_microbiome_interactions.tsv"), emit: interactions
    path "versions.yml", emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def prefix = task.ext.prefix ?: "${meta.id}"
    def microberx_min_score = params.microberx_min_score ?: 0.3
    def high_threshold = params.interaction_high_threshold ?: 0.7
    def medium_threshold = params.interaction_medium_threshold ?: 0.4
    """
    microberx_predict.py \\
        --sample-id ${meta.id} \\
        --consensus-taxonomy ${consensus_taxonomy} \\
        --drugs-with-smiles ${drugs_with_smiles} \\
        --pathabundance ${pathabundance} \\
        --microberx-min-score ${microberx_min_score} \\
        --high-threshold ${high_threshold} \\
        --medium-threshold ${medium_threshold} \\
        --output ${prefix}.drug_microbiome_interactions.tsv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "\$(python --version | sed 's/Python //g')"
        pandas: "\$(python -c 'import pandas as pd; print(pd.__version__)')"
    END_VERSIONS
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    cat <<-EOF > ${prefix}.drug_microbiome_interactions.tsv
    sample_id	drug_name	drugbank_id	drug_class	species	taxonomic_confidence	microberx_score	pathway_coverage_weight	interaction_confidence	risk_tier
    ${meta.id}	STUB_DRUG	DBSTUB	stub_class	stub_species	MEDIUM	0.5	1.0	0.25	LOW
    EOF

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
        pandas: "stub"
    END_VERSIONS
    """
}
