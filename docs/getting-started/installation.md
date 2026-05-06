# Installation

## Requirements

| Dependency | Minimum version | Notes |
|-----------|----------------|-------|
| Nextflow | 23.04 | `curl -s https://get.nextflow.io | bash` |
| Docker Desktop | 24.x | or Singularity / Conda |
| Java | 17 | bundled with Nextflow installer |
| Python | 3.10+ | only needed for local SMILES pre-resolution |
| RAM | 16 GB | 32+ GB recommended for KneadData + Kraken2 |
| Disk | 50 GB free | for databases and intermediate files |

## 1 — Install Nextflow

```bash
curl -s https://get.nextflow.io | bash
chmod +x nextflow
sudo mv nextflow /usr/local/bin/
nextflow -version
```

## 2 — Install Docker Desktop

Download from [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/).

!!! warning "Docker Desktop resource allocation"
    RxBiome processes need at least **6 GB of RAM** and **4 CPUs** allocated to Docker Desktop.  
    Go to **Docker Desktop → Settings → Resources** and set appropriate values before running.

## 3 — Clone the Repository

```bash
git clone https://github.com/sanyabadole/RxBiome.git rxbiome
cd rxbiome
```

## 4 — Verify the Installation

Run the bundled test profile (stub data, no databases required):

```bash
nextflow run main.nf -profile test,docker --outdir results_test
```

A successful run prints:
```
-[rxbiome] Pipeline completed successfully-
```

## 5 — (Optional) Install Python dependencies for SMILES pre-resolution

```bash
pip install requests
```

This is only needed if you want to pre-resolve SMILES locally before a pipeline run. Inside the pipeline, all Python tools run inside their own Docker containers.

## Updating

Pull the latest code and Docker images:

```bash
cd rxbiome
git pull origin dev
nextflow pull .
```

## Using Conda Instead of Docker

```bash
nextflow run main.nf -profile conda --input samplesheet.csv ...
```

!!! note
    Conda environments are built on first run and cached in `work/conda/`. Expect 10–20 minutes extra on the first execution.
