process DRUG_SMILES_LOOKUP {
    tag "drug_smiles_lookup"
    label 'process_low'

    conda "conda-forge::python=3.11"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
    'https://depot.galaxyproject.org/singularity/pandas:2.2.1' :
    'biocontainers/pandas:2.2.1' }"

    input:
    path drug_library_csv
    val api_key

    output:
    path "drugs_with_smiles.tsv", emit: drugs_with_smiles
    path "versions.yml", emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    """
    drug_smiles_lookup.py \\
        --drug-library ${drug_library_csv} \\
        --api-key "${api_key ?: ''}" \\
        --output drugs_with_smiles.tsv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "\$(python --version | sed 's/Python //g')"
        lookup_sources: "drugbank,pubchem,chembl"
    END_VERSIONS
    """

    stub:
    """
    python - <<'PY'
    import csv
    with open("${drug_library_csv}", "r", encoding="utf-8", newline="") as inp, open("drugs_with_smiles.tsv", "w", encoding="utf-8", newline="") as out:
        r = csv.DictReader(inp)
        w = csv.DictWriter(out, fieldnames=["drug_name", "drugbank_id", "drug_class", "smiles"], delimiter="\\t")
        w.writeheader()
        for row in r:
            w.writerow({
                "drug_name": row.get("drug_name", ""),
                "drugbank_id": row.get("drugbank_id", ""),
                "drug_class": row.get("drug_class", ""),
                "smiles": ""
            })
    PY

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
        lookup_sources: "stub"
    END_VERSIONS
    """
}
