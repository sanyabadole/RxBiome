process PK_REPORT_PLOTS {
    tag "pk_report_plots"
    label 'process_low'

    conda "conda-forge::python=3.11 conda-forge::pandas=2.2.1"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
    'https://depot.galaxyproject.org/singularity/pandas:2.2.1' :
    'biocontainers/pandas:2.2.1' }"

    input:
    path(cohort_drug_summary)
    path(cohort_sample_summary)

    output:
    path("cohort.drug_dose_change.svg"), emit: drug_plot
    path("cohort.sample_max_dose_change.svg"), emit: sample_plot
    path("versions.yml"), emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    """
    pk_report_plots.py \\
      --cohort-drug-summary ${cohort_drug_summary} \\
      --cohort-sample-summary ${cohort_sample_summary} \\
      --drug-plot-output cohort.drug_dose_change.svg \\
      --sample-plot-output cohort.sample_max_dose_change.svg

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "\$(python --version | sed 's/Python //g')"
        pandas: "\$(python -c 'import pandas as pd; print(pd.__version__)')"
    END_VERSIONS
    """

    stub:
    """
    cat <<-EOF > cohort.drug_dose_change.svg
    <svg xmlns="http://www.w3.org/2000/svg" width="400" height="120"><text x="10" y="20">stub cohort drug plot</text></svg>
    EOF
    cat <<-EOF > cohort.sample_max_dose_change.svg
    <svg xmlns="http://www.w3.org/2000/svg" width="400" height="120"><text x="10" y="20">stub cohort sample plot</text></svg>
    EOF

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
        pandas: "stub"
    END_VERSIONS
    """
}
