process PK_REPORT_SAMPLE {
    tag "${meta.id}"
    label 'process_low'

    // pandas image already used by PK_IMPACT; jinja2 is installed on-the-fly
    // in the script block if absent (mirrors the matplotlib approach for
    // PK_REPORT_PLOTS).
    conda "conda-forge::python=3.11 conda-forge::pandas=2.2.1 conda-forge::jinja2=3.1"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/pandas:2.2.1' :
        'biocontainers/pandas:2.2.1' }"

    input:
    tuple val(meta), path(pk_impact_tsv), path(pk_summary_tsv), path(dose_plot_svg), path(risk_plot_svg)

    output:
    tuple val(meta), path("*.qc_report.html"), emit: qc_report
    path "versions.yml",                       emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    # Install jinja2 into a local target directory if the container lacks it.
    python - <<'PY'
    import importlib, os, subprocess, sys
    try:
        importlib.import_module("jinja2")
    except ModuleNotFoundError:
        target = os.path.join(os.getcwd(), ".pylibs")
        os.makedirs(target, exist_ok=True)
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                               "--quiet", "--target", target, "jinja2"])
    PY

    if [[ -n "\${PYTHONPATH:-}" ]]; then
      export PYTHONPATH="\$PWD/.pylibs:\$PYTHONPATH"
    else
      export PYTHONPATH="\$PWD/.pylibs"
    fi

    pk_report_sample.py \\
        --sample-id      ${meta.id}       \\
        --pk-impact-tsv  ${pk_impact_tsv} \\
        --pk-summary-tsv ${pk_summary_tsv} \\
        --dose-plot-svg  ${dose_plot_svg}  \\
        --risk-plot-svg  ${risk_plot_svg}  \\
        --output         ${prefix}.qc_report.html

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "\$(python --version | sed 's/Python //g')"
        jinja2: "\$(python -c 'import jinja2; print(jinja2.__version__)')"
        pandas: "\$(python -c 'import pandas as pd; print(pd.__version__)')"
    END_VERSIONS
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    cat <<-EOF > ${prefix}.qc_report.html
    <!DOCTYPE html>
    <html>
      <body>
        <h1>Stub QC Report</h1>
        <p>Sample: ${meta.id}</p>
      </body>
    </html>
    EOF

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
        jinja2: "stub"
        pandas: "stub"
    END_VERSIONS
    """
}
