process PK_REPORT_AGGREGATE {
    tag "pk_report_aggregate"
    label 'process_low'

    conda "conda-forge::python=3.11 conda-forge::pandas=2.2.1"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
    'https://depot.galaxyproject.org/singularity/pandas:2.2.1' :
    'biocontainers/pandas:2.2.1' }"

    input:
    path(pk_impact_files)

    output:
    path("cohort.pk_impact.tsv"), emit: cohort_pk_impact
    path("cohort.drug_summary.tsv"), emit: cohort_drug_summary
    path("cohort.sample_summary.tsv"), emit: cohort_sample_summary
    path("versions.yml"), emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def files_arg = pk_impact_files.collect { it.toString() }.join(' ')
    """
    pk_report_aggregate.py \\
      --pk-impact-files ${files_arg} \\
      --cohort-pk-impact-output cohort.pk_impact.tsv \\
      --cohort-drug-summary-output cohort.drug_summary.tsv \\
      --cohort-sample-summary-output cohort.sample_summary.tsv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "\$(python --version | sed 's/Python //g')"
        pandas: "\$(python -c 'import pandas as pd; print(pd.__version__)')"
    END_VERSIONS
    """

    stub:
    """
    cat <<-EOF > cohort.pk_impact.tsv
    sample_id	drug_name	drugbank_id	standard_dose_mg	microbiome_impact_factor	predicted_clearance_multiplier	predicted_auc_multiplier	recommended_dose_mg	recommended_dose_change_fraction	confidence_low	confidence_high	pk_risk_tier	dominant_species	mechanistic_note
    STUB_SAMPLE	STUB_DRUG	DBSTUB	100	0.4	0.95	1.05	95	-0.05	85	105	MEDIUM	stub_species	stub note
    EOF
    cat <<-EOF > cohort.drug_summary.tsv
    drug_name	drugbank_id	n_samples	mean_recommended_dose_change_fraction	mean_predicted_auc_multiplier	high_risk_count	medium_risk_count	low_risk_count
    STUB_DRUG	DBSTUB	1	-0.05	1.05	0	1	0
    EOF
    cat <<-EOF > cohort.sample_summary.tsv
    sample_id	n_drugs	mean_recommended_dose_change_fraction	max_abs_recommended_dose_change_fraction	high_risk_count	medium_risk_count	low_risk_count
    STUB_SAMPLE	1	-0.05	0.05	0	1	0
    EOF

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
        pandas: "stub"
    END_VERSIONS
    """
}
