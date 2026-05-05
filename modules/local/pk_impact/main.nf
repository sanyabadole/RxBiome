process PK_IMPACT {
    tag "${meta.id}"
    label 'process_low'

    conda "conda-forge::python=3.11 conda-forge::pandas=2.2.1 conda-forge::numpy=1.26.4"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
    'https://depot.galaxyproject.org/singularity/pandas:2.2.1' :
    'biocontainers/pandas:2.2.1' }"

    input:
    tuple val(meta), path(interactions), path(drug_pk_metadata)

    output:
    tuple val(meta), path("*.pk_impact.tsv"), emit: pk_impact
    tuple val(meta), path("*.pk_summary.tsv"), emit: pk_summary
    tuple val(meta), path("*.dose_change.svg"), emit: dose_plot
    tuple val(meta), path("*.risk_tier_counts.svg"), emit: risk_plot
    path "versions.yml", emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def prefix = task.ext.prefix ?: "${meta.id}"
    def target_exposure_multiplier = params.pk_target_exposure_multiplier != null ? params.pk_target_exposure_multiplier : 1.0
    def max_dose_adjustment_fraction = params.pk_max_dose_adjustment_fraction != null ? params.pk_max_dose_adjustment_fraction : 0.5
    def min_confidence_interval_width = params.pk_min_confidence_interval_width != null ? params.pk_min_confidence_interval_width : 0.1
    """
    pk_impact.py \\
        --sample-id ${meta.id} \\
        --interactions ${interactions} \\
        --drug-pk-metadata ${drug_pk_metadata} \\
        --target-exposure-multiplier ${target_exposure_multiplier} \\
        --max-dose-adjustment-fraction ${max_dose_adjustment_fraction} \\
        --min-confidence-interval-width ${min_confidence_interval_width} \\
        --output ${prefix}.pk_impact.tsv \\
        --summary-output ${prefix}.pk_summary.tsv \\
        --dose-plot-output ${prefix}.dose_change.svg \\
        --risk-plot-output ${prefix}.risk_tier_counts.svg

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "\$(python --version | sed 's/Python //g')"
        pandas: "\$(python -c 'import pandas as pd; print(pd.__version__)')"
        numpy: "\$(python -c 'import numpy as np; print(np.__version__)')"
    END_VERSIONS
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    cat <<-EOF > ${prefix}.pk_impact.tsv
    sample_id	drug_name	drugbank_id	standard_dose_mg	microbiome_impact_factor	predicted_clearance_multiplier	predicted_auc_multiplier	recommended_dose_mg	recommended_dose_change_fraction	confidence_low	confidence_high	pk_risk_tier	dominant_species	mechanistic_note
    ${meta.id}	STUB_DRUG	DBSTUB	100	0.4	0.95	1.05	95	-0.05	85	105	MEDIUM	stub_species	stub note
    EOF
    cat <<-EOF > ${prefix}.pk_summary.tsv
    sample_id	n_drugs	mean_dose_change_fraction	max_abs_dose_change_fraction	n_high_risk	n_medium_risk	n_low_risk
    ${meta.id}	1	-0.05	0.05	0	1	0
    EOF
    cat <<-EOF > ${prefix}.dose_change.svg
    <svg xmlns="http://www.w3.org/2000/svg" width="400" height="120"><text x="10" y="20">stub dose plot</text></svg>
    EOF
    cat <<-EOF > ${prefix}.risk_tier_counts.svg
    <svg xmlns="http://www.w3.org/2000/svg" width="400" height="120"><text x="10" y="20">stub risk plot</text></svg>
    EOF

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
        pandas: "stub"
        numpy: "stub"
    END_VERSIONS
    """
}
