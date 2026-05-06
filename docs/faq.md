# Frequently Asked Questions

## Pipeline Execution

??? question "The pipeline hangs at KneadData for hours with no output."
    This is almost always a Docker Desktop resource problem. Check:
    ```bash
    docker stats
    ```
    If memory shows 0 B or CPUs show 0, Docker Desktop has crashed or has insufficient resources. See [Docker Images](docker.md) for recommended settings.

??? question "I get `Process requirement exceeds available memory`."
    Your Docker Desktop memory allocation is lower than what the process requests.
    Either increase Docker Desktop memory, or cap resources explicitly:
    ```bash
    nextflow run main.nf --max_memory 10.GB --max_cpus 4 ...
    ```

??? question "The pipeline fails with `PYTHONPATH: unbound variable`."
    This was a bug in an older version of `PK_REPORT_SAMPLE`. Update to the latest commit on `dev`:
    ```bash
    git pull origin dev
    ```

??? question "How do I resume after a failure?"
    ```bash
    nextflow run main.nf [same args] -resume
    ```
    Nextflow caches all completed tasks in `work/`. `-resume` re-runs only from the point of failure.

??? question "The pipeline printed a warning about missing PK metadata for a drug."
    Your `--drug_pk_metadata` file doesn't include a row for that drug. A fallback of 500 mg standard dose is used. Add the drug to your PK metadata CSV for more accurate dose adjustment recommendations.

---

## Input Files

??? question "My drug library CSV isn't being read correctly."
    The pipeline auto-detects whether the file is comma- or tab-separated. If resolution still fails, verify:
    - Header row is present: `drug_name,drugbank_id,drug_class,smiles`
    - No byte-order marks (BOM) in the file: `file -i my_drugs.csv`
    - No Windows line endings: `dos2unix my_drugs.csv`

??? question "Can I use single-end data?"
    Yes. Omit the `fastq_2` column in your samplesheet:
    ```csv
    sample,fastq_1,fastq_2
    SAMPLE_01,/data/reads.fastq.gz,
    ```
    Also pass `--sequencing_type single`.

??? question "Can I have multiple sequencing runs for the same sample?"
    Yes. Use the same `sample` value in multiple samplesheet rows. The pipeline concatenates FASTQ files per unique sample before processing.

---

## Databases

??? question "Where do I download the Kraken2 Standard 8 GB database?"
    ```bash
    wget https://genome-idx.s3.amazonaws.com/kraken/k2_standard_08gb_20240112.tar.gz
    tar -xzf k2_standard_08gb_20240112.tar.gz -C databases/kraken2/
    ```

??? question "Do I need HUMAnN3 databases?"
    No. HUMAnN3 is fully optional. If you omit `--humann3_nucleotide_db` and `--humann3_protein_db`, functional profiling is skipped and the pipeline continues without it. PK impact modelling does not require HUMAnN3 output.

??? question "Can I build my own Kraken2 database?"
    Yes. Use the patched Kraken2 image in `docker/kraken2/` to avoid FTP download failures. See [docker/kraken2/README.md](https://github.com/sanyabadole/RxBiome/blob/dev/docker/kraken2/README.md).

---

## Results

??? question "Where is the per-patient HTML report?"
    ```
    results/pk_impact/{sample}.qc_report.html
    ```
    It is fully self-contained — no external dependencies. Open it in any browser or email it directly.

??? question "All my samples show LOW risk. Does that mean the microbiome has no effect?"
    Not necessarily. Check:
    1. Were SMILES resolved for all drugs? (look for empty `smiles` in your resolved drug library)
    2. Are Kraken2/MetaPhlAn profiles non-empty? (check `consensus_taxonomy.tsv`)
    3. Is the MIF score > 0 in `interactions.tsv`? If MIF = 0 for all drugs, MicrobeRX found no interactions.
    
    The model is conservative by design. LOW tier means the predicted microbiome contribution to PK variability is below 10%.

??? question "How do I interpret a negative dose adjustment?"
    A negative `dose_adj_fraction` means the model predicts the microbiome is *reducing* drug exposure (AUC ↓ — higher clearance). This suggests a potential dose *increase* may be needed to maintain therapeutic levels.

---

## Development

??? question "How do I add a new drug to the interaction database?"
    Add a row to your drug library CSV with the drug's `drugbank_id`. Run `bin/drug_smiles_lookup.py` to pre-resolve SMILES, then re-run the pipeline.

??? question "How do I run the unit tests?"
    ```bash
    cd tests/pytest
    pip install pytest pandas numpy matplotlib seaborn
    pytest test_pk_impact_models.py -v
    ```

??? question "How do I lint the code before a PR?"
    ```bash
    pip install ruff
    ruff check bin/
    ```
