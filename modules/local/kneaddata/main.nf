// KneadData: VEuPathDB humann-nextflow pattern (plain FASTQ, -o ., --bypass-trf in kneaddataCommand).
process KNEADDATA {
    tag "$meta.id"
    label 'process_medium'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/kneaddata:0.12.0--pyhdfd78af_1' :
        'quay.io/biocontainers/kneaddata:0.12.0--pyhdfd78af_1' }"

    input:
    tuple val(meta), path(reads)
    path  host_db

    output:
    tuple val(meta), path("*_paired_*.fastq.gz"), emit: reads
    tuple val(meta), path("*.log"),                         emit: log
    tuple val("${task.process}"), val('kneaddata'), eval('kneaddata --version 2>&1 | head -1'), emit: versions_kneaddata, topic: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args   = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    if (meta.single_end) {
        """
        set -euo pipefail
        export TMPDIR="\$(pwd)"

        zcat ${reads[0]} > ${prefix}_1.fastq

        kneaddata \\
            --unpaired ${prefix}_1.fastq \\
            --reference-db ${host_db} \\
            -o . \\
            --output-prefix ${prefix} \\
            --threads ${task.cpus} \\
            --bypass-trim \\
            --bypass-trf \\
            ${args}

        rm -f ${prefix}_1.fastq
        for f in ${prefix}_paired_*.fastq ${prefix}.fastq; do
            [ -f "\$f" ] || continue
            gzip -f "\$f"
        done
        if [ -f ${prefix}.fastq.gz ] && [ ! -f ${prefix}_paired_1.fastq.gz ]; then
            mv ${prefix}.fastq.gz ${prefix}_paired_1.fastq.gz
        fi
        """
    } else {
        """
        set -euo pipefail
        export TMPDIR="\$(pwd)"

        zcat ${reads[0]} > ${prefix}_1.fastq
        zcat ${reads[1]} > ${prefix}_2.fastq

        kneaddata \\
            --input1 ${prefix}_1.fastq \\
            --input2 ${prefix}_2.fastq \\
            --reference-db ${host_db} \\
            -o . \\
            --output-prefix ${prefix} \\
            --threads ${task.cpus} \\
            --bypass-trim \\
            --bypass-trf \\
            ${args}

        rm -f ${prefix}_1.fastq ${prefix}_2.fastq
        for f in ${prefix}_paired_*.fastq; do
            [ -f "\$f" ] || continue
            gzip -f "\$f"
        done
        """
    }

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    echo '' | gzip > ${prefix}_paired_1.fastq.gz
    echo '' | gzip > ${prefix}_paired_2.fastq.gz
    touch "${prefix}.log"
    """
}
